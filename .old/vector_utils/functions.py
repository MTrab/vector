"""For handling the randominess in Vectors chatting and responses."""
from __future__ import annotations

import ha_vector


async def get_stats(conn) -> ha_vector.messaging.protocol.PullJdocsResponse:
    """Get stats from Vector."""
    req = ha_vector.messaging.protocol.PullJdocsRequest(
        jdoc_types=[
            ha_vector.messaging.settings_pb2.ROBOT_SETTINGS,
            ha_vector.messaging.settings_pb2.ROBOT_LIFETIME_STATS,
            ha_vector.messaging.settings_pb2.ACCOUNT_SETTINGS,
            ha_vector.messaging.settings_pb2.USER_ENTITLEMENTS,
        ]
    )
    return await conn.grpc_interface.PullJdocs(req)
