# Copyright 2021 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from http import HTTPStatus

import synapse.rest.admin
from synapse.api.errors import Codes
from synapse.rest.client import login
from synapse.server import HomeServer
from synapse.types import JsonDict

from tests import unittest


class FederationTestCase(unittest.HomeserverTestCase):
    servlets = [
        synapse.rest.admin.register_servlets,
        login.register_servlets,
    ]

    def prepare(self, reactor, clock, hs: HomeServer):
        self.store = hs.get_datastore()
        self.admin_user = self.register_user("admin", "pass", admin=True)
        self.admin_user_tok = self.login("admin", "pass")

        self.url = "/_synapse/admin/v1/federation/destinations"

    def test_requester_is_no_admin(self):
        """
        If the user is not a server admin, an error 403 is returned.
        """

        self.register_user("user", "pass", admin=False)
        other_user_tok = self.login("user", "pass")

        channel = self.make_request(
            "GET",
            self.url,
            content={},
            access_token=other_user_tok,
        )

        self.assertEqual(HTTPStatus.FORBIDDEN, channel.code, msg=channel.json_body)
        self.assertEqual(Codes.FORBIDDEN, channel.json_body["errcode"])

    def test_invalid_parameter(self):
        """
        If parameters are invalid, an error is returned.
        """

        # negative limit
        channel = self.make_request(
            "GET",
            self.url + "?limit=-5",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, channel.code, msg=channel.json_body)
        self.assertEqual(Codes.INVALID_PARAM, channel.json_body["errcode"])

        # negative from
        channel = self.make_request(
            "GET",
            self.url + "?from=-5",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, channel.code, msg=channel.json_body)
        self.assertEqual(Codes.INVALID_PARAM, channel.json_body["errcode"])

        # unkown order_by
        channel = self.make_request(
            "GET",
            self.url + "?order_by=bar",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, channel.code, msg=channel.json_body)
        self.assertEqual(Codes.UNKNOWN, channel.json_body["errcode"])

        # invalid search order
        channel = self.make_request(
            "GET",
            self.url + "?dir=bar",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, channel.code, msg=channel.json_body)
        self.assertEqual(Codes.UNKNOWN, channel.json_body["errcode"])

    def test_limit(self):
        """
        Testing list of users with limit
        """

        number_destinations = 20
        self._create_destinations(number_destinations)

        channel = self.make_request(
            "GET",
            self.url + "?limit=5",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), 5)
        self.assertEqual(channel.json_body["next_token"], "5")
        self._check_fields(channel.json_body["destinations"])

    def test_from(self):
        """
        Testing list of users with a defined starting point (from)
        """

        number_destinations = 20
        self._create_destinations(number_destinations)

        channel = self.make_request(
            "GET",
            self.url + "?from=5",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), 15)
        self.assertNotIn("next_token", channel.json_body)
        self._check_fields(channel.json_body["destinations"])

    def test_limit_and_from(self):
        """
        Testing list of users with a defined starting point and limit
        """

        number_destinations = 20
        self._create_destinations(number_destinations)

        channel = self.make_request(
            "GET",
            self.url + "?from=5&limit=10",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(channel.json_body["next_token"], "15")
        self.assertEqual(len(channel.json_body["destinations"]), 10)
        self._check_fields(channel.json_body["destinations"])

    def test_next_token(self):
        """
        Testing that `next_token` appears at the right place
        """

        number_destinations = 20
        self._create_destinations(number_destinations)

        #  `next_token` does not appear
        # Number of results is the number of entries
        channel = self.make_request(
            "GET",
            self.url + "?limit=20",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), number_destinations)
        self.assertNotIn("next_token", channel.json_body)

        #  `next_token` does not appear
        # Number of max results is larger than the number of entries
        channel = self.make_request(
            "GET",
            self.url + "?limit=21",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), number_destinations)
        self.assertNotIn("next_token", channel.json_body)

        #  `next_token` does appear
        # Number of max results is smaller than the number of entries
        channel = self.make_request(
            "GET",
            self.url + "?limit=19",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), 19)
        self.assertEqual(channel.json_body["next_token"], "19")

        # Check
        # Set `from` to value of `next_token` for request remaining entries
        #  `next_token` does not appear
        channel = self.make_request(
            "GET",
            self.url + "?from=19",
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(channel.json_body["total"], number_destinations)
        self.assertEqual(len(channel.json_body["destinations"]), 1)
        self.assertNotIn("next_token", channel.json_body)

    def test_list_all_destinations(self):
        """
        List all destinations.
        """
        number_destinations = 5
        self._create_destinations(number_destinations)

        channel = self.make_request(
            "GET",
            self.url,
            {},
            access_token=self.admin_user_tok,
        )

        self.assertEqual(HTTPStatus.OK, channel.code, msg=channel.json_body)
        self.assertEqual(number_destinations, len(channel.json_body["destinations"]))
        self.assertEqual(number_destinations, channel.json_body["total"])

        # Check that all fields are available
        self._check_fields(channel.json_body["destinations"])

    def _create_destinations(self, number_destinations: int):
        """"""
        for i in range(1, number_destinations + 1):
            dest = f"sub{i}.example.com"
            now_ms = self.clock.time_msec()
            d = self.store.set_destination_retry_timings(
                dest, now_ms, 1000000000 - now_ms, 100 * i
            )
            self.get_success(d)

            d = self.store.set_destination_last_successful_stream_ordering(
                dest, 100 * i
            )
            self.get_success(d)

    def _check_fields(self, content: JsonDict):
        """Checks that the expected destination attributes are present in content
        Args:
            content: List that is checked for content
        """
        for c in content:
            self.assertIn("destination", c)
            self.assertIn("retry_last_ts", c)
            self.assertIn("retry_interval", c)
            self.assertIn("failure_ts", c)
            self.assertIn("last_successful_stream_ordering", c)

