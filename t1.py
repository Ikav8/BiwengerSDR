import bw_api as bw_api
from pprint import pprint


# movimientos #
movs = bw_api.get_movs()
print(pprint(movs))


df_liga_y_balances = bw_api.get_liga_y_balances()
print(df_liga_y_balances.to_string())
# balances #
balances = bw_api.print_balances()
with open('balances.txt', 'w', encoding='UTF8') as balances_file:
    balances_file.writelines("\n".join(balances))


# jugadores #
# jugadores = bw_api.get_jugadores()
# print(pprint(jugadores))


# print(bw_api.get_balances())
# print(bw_api.get_liga())


