from app.realtime.hub import InMemoryRealtimeHub, RealtimeHub


# Único punto de composición del adaptador. Los servicios funcionales dependen
# del puerto RealtimeHub y no de las estructuras internas del hub en memoria.
realtime_hub: RealtimeHub = InMemoryRealtimeHub()
