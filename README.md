# Redis OTFA (on-the-fly auth)

Proof of concept that a restricted default user could send a request to add a user over a stream.

Planned use is an ephemeral server whereby Redis is used as the transaction layer, anyone is allowed to join, but we want to mitigate spoofing another user's commands.