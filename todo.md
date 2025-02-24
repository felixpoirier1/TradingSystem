# TODO

- [ ] modify gateways (esp. Kalshi & Polymarket) to use asyncio & websockets instead of threads & websocket-client
- [ ] implement asyncio in engine
- [ ] explore uvloop as an alternative to asyncio
- [ ] run a profiler to check for bottlenecks
- [ ] outsource I/O operations to a separate process (e.g. websockets)