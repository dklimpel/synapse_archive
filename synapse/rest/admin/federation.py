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
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Tuple

from synapse.api.errors import Codes, SynapseError
from synapse.http.servlet import RestServlet, parse_integer, parse_string
from synapse.http.site import SynapseRequest
from synapse.rest.admin._base import admin_patterns, assert_requester_is_admin
from synapse.storage.databases.main.transactions import DestinationSortOrder
from synapse.types import JsonDict

if TYPE_CHECKING:
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)


class FederationDestinationRestServlet(RestServlet):
    """Get request to list all local users.
    This needs user to have administrator access in Synapse.

    GET /_synapse/admin/v1/federation/destinations?from=0&limit=10

    returns:
        200 OK with list of users if success otherwise an error.

    The parameters `from` and `limit` are required only for pagination.
    By default, a `limit` of 100 is used.
    The parameter `name` can be used to filter by user id or display name.
    The parameter `order_by` can be used to order the result.
    """

    PATTERNS = admin_patterns("/federation/destinations$")

    def __init__(self, hs: "HomeServer"):
        self._auth = hs.get_auth()
        self._store = hs.get_datastore()

    async def on_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        await assert_requester_is_admin(self._auth, request)

        start = parse_integer(request, "from", default=0)
        limit = parse_integer(request, "limit", default=100)

        if start < 0:
            raise SynapseError(
                400,
                "Query parameter from must be a string representing a positive integer.",
                errcode=Codes.INVALID_PARAM,
            )

        if limit < 0:
            raise SynapseError(
                400,
                "Query parameter limit must be a string representing a positive integer.",
                errcode=Codes.INVALID_PARAM,
            )

        destination = parse_string(request, "destination")

        order_by = parse_string(
            request,
            "order_by",
            default=DestinationSortOrder.DESTINATION.value,
            allowed_values=(
                DestinationSortOrder.DESTINATION.value,
                DestinationSortOrder.RETRY_LAST_TS.value,
                DestinationSortOrder.RETTRY_INTERVAL.value,
                DestinationSortOrder.FAILURE_TS.value,
                DestinationSortOrder.LAST_SUCCESSFUL_STREAM_ORDERING.value,
            ),
        )

        direction = parse_string(request, "dir", default="f", allowed_values=("f", "b"))

        destinations, total = await self._store.get_destinations_paginate(
            start, limit, destination, order_by, direction
        )
        response = {"destinations": destinations, "total": total}
        if (start + limit) < total:
            response["next_token"] = str(start + len(destinations))

        return HTTPStatus.OK, response
