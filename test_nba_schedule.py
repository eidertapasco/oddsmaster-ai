# test_nba_schedule.py
from nba_schedule import obtener_nba_completo

data = obtener_nba_completo()
print(f"Programados hoy: {len(data['programados'])}")
print(f"En vivo ahora:   {len(data['en_vivo'])}")
print(f"Finalizados:     {len(data['finalizados'])}")

for p in data["programados"]:
    print(f"  📅 {p['local']} vs {p['visitante']} — {p['hora']}")
for p in data["en_vivo"]:
    print(f"  🔴 {p['local']} vs {p['visitante']} — {p['puntos_local']}-{p['puntos_visitante']}")
    
# test_nba_schedule.py — agrega esto al final para ver la estructura real
from nba_schedule import obtener_partidos_nba_hoy
todos = obtener_partidos_nba_hoy()
if todos:
    import json
    print("\nEstructura del primer partido:")
    print(json.dumps(todos[0], indent=2))