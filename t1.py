import bw_api as bw_api
from pprint import pprint


# movimientos #
movs = bw_api.get_movs()
print(pprint(movs))

df_liga_y_balances = bw_api.get_liga_y_balances()
print(df_liga_y_balances.to_string())




# print(bw_api.get_jugadores_info())

# jugadores #
# jugadores = bw_api.get_jugadores()
# print(pprint(jugadores))


