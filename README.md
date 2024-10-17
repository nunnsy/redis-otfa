# Redis OTFA (on-the-fly auth)

Proof of concept that a restricted default user could send a request to add a user over a stream.

Planned use is an ephemeral server whereby Redis is used as the transaction layer, anyone is allowed to join, but we want to mitigate spoofing another user's commands.

At minimum, the `redis.conf` associated with the instance must contain a definition for an administrator, as well as restrictive commands for the default user:
```
user admin allcommands allkeys allchannels on >admin
user default reset +SISMEMBER %R~otfa_users +XADD %W~otfa_request on nopass
```