import pandas as pd
import requests
from datetime import datetime
import config as bw_config

class movimiento:
    def __init__(self, usuario, balance, detalles):
        self.usuario = usuario
        self.balance = int(balance)
        self.detalles = detalles

    def __str__(self):
        signo = '+' if int(self.balance) > 0 else '-'
        return("[" + signo + "] " + self.usuario + " [ " + '{:,} €'.format(self.balance).replace(',', '.') + " ] (" + self.detalles + ")")

    def __repr__(self):
        signo = '+' if self.balance > 0 else '-'
        return("[" + signo + "] " + self.usuario + " [ " + '{:,} €'.format(self.balance).replace(',', '.')  + " ] (" + self.detalles + ")")

    def to_dict(self):
        return {
            'usuario' : self.usuario,
            'balance' : self.balance
        }

ids_usuarios = bw_config.IDS_USUARIOS
movs_iniciales = bw_config.MOVS_INICIALES

def get_jugadores():

    url_jugadores = 'https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=es&score=2'
    r = requests.get(url=url_jugadores)

    jugadores_data = r.json()

    posiciones = {1: 'PT', 2: 'DF', 3: 'MC', 4: 'DL', 5: 'CO'}

    jugadores = jugadores_data.get('data').get('players')
    jugadores_dict = {}
    for jugador_id in jugadores:
        jugador = jugadores.get(jugador_id, '-')
        jugador_nombre = jugador.get('name', '-')
        jugador_posicion_num = jugador.get('position')
        jugador_posicion_texto = posiciones.get(jugador_posicion_num)
        jugador_info = jugador_nombre + " [" + jugador_posicion_texto + "]"
        jugadores_dict[jugador_id] = jugador_info

    return jugadores_dict

def get_liga():
    url_liga = "https://biwenger.as.com/api/v2/league?include=all&fields=*,standings,tournaments,group,settings(description)"
    headers = bw_config.BOARD_HEADERS
    r = requests.get(url=url_liga, headers=headers)
    json_data = r.json()
    standings_lista = []
    for user in json_data['data']['standings']:
        user_id = str(user['id'])
        usuario = ids_usuarios[user_id]
        pts = user['points']
        nro_jugadores = user['teamSize']
        valor_equipo = user['teamValue']
        standings_lista.append([usuario, pts, nro_jugadores, valor_equipo])

    df = pd.DataFrame(standings_lista, columns=['usuario', 'pts', 'nro_jugadores', 'valor_equipo'])

    return df

def get_movs():

    url_fichajes = 'https://biwenger.as.com/api/v2/league/764690/board'
    params = {'offset': 0, 'limit': 10000}
    headers = bw_config.BOARD_HEADERS
    r = requests.get(url=url_fichajes, params=params, headers=headers)
    json_data = r.json()

    lista_jugadores = get_jugadores()

    movs = []
    for data_item_bloque in json_data.get('data'):
        if data_item_bloque['date'] <= 1628022510: # fecha reinicio liga #
            break

        # transfer -- usuario -> usuario // usuario -> mercado
        if data_item_bloque['type'] == 'transfer':
            for transfer_item in data_item_bloque['content']:
                # from #
                id_usuario_from = str(transfer_item['from']['id'])
                nombre_usuario_from = ids_usuarios[id_usuario_from]
                balance = transfer_item['amount']
                jugador_id = transfer_item['player']
                jugador_info = lista_jugadores.get(str(jugador_id))
                movs.append(
                    movimiento(usuario=nombre_usuario_from,
                               balance=balance,
                               detalles=nombre_usuario_from + " vende a " + jugador_info)
                )

                # to ? #
                id_usuario_to = transfer_item.get('to', 'ERROR')
                if id_usuario_to != 'ERROR':
                    nombre_usuario_to = ids_usuarios[str(id_usuario_to['id'])]
                    movs.append(
                        movimiento(usuario=nombre_usuario_to,
                                   balance=balance * -1,
                                   detalles=nombre_usuario_to + " ficha a " + jugador_info)
                    )

        # market -- mercado -> jugador
        if data_item_bloque['type'] == 'market':
            for market_item in data_item_bloque['content']:
                # to #
                id_usuario_to = str(market_item['to']['id'])
                nombre_usuario_to = ids_usuarios[id_usuario_to]
                balance = market_item['amount']
                jugador_id = market_item['player']
                jugador_info = lista_jugadores.get(str(jugador_id))
                movs.append(
                    movimiento(usuario=nombre_usuario_to,
                               balance=balance * -1,
                               detalles=nombre_usuario_to + " ficha a " + jugador_info)
                )

        # roundFinished
        if data_item_bloque['type'] == 'roundFinished':
            nombre_jornada = data_item_bloque.get('content').get('round').get('name')
            resultados = data_item_bloque['content']['results']
            for resultado in resultados:
                user_id = str(resultado['user']['id'])
                user_nombre = ids_usuarios[user_id]
                dinero = resultado['bonus']
                movs.append(
                    movimiento(usuario=user_nombre,
                               balance=dinero,
                               detalles=nombre_jornada)
                )


        # loan (cesion)
        if data_item_bloque['type'] == 'loan':
            for loan_item in data_item_bloque['content']:
                id_usuario_from = str(loan_item['from']['id'])
                nombre_usuario_from = ids_usuarios[id_usuario_from]

                id_usuario_to = str(loan_item['to']['id'])
                nombre_usuario_to = ids_usuarios[id_usuario_to]

                jugador_id = loan_item['player']
                jugador_info = lista_jugadores.get(str(jugador_id))

                detalles = nombre_usuario_from + " cede a " + nombre_usuario_to + " a " + jugador_info
                dinero = loan_item['amount']
                movs.append(
                    movimiento(usuario=nombre_usuario_from,
                               balance=dinero,
                               detalles=detalles)
                )
                movs.append(
                    movimiento(usuario=nombre_usuario_to,
                               balance=dinero * -1,
                               detalles=detalles)
                )


    movs_todos = movs_iniciales + movs
    return movs_todos

def print_balances():
    movs = get_movs()
    df = pd.DataFrame.from_records([m.to_dict() for m in movs])
    df['balance'] = df['balance'].astype('int64')
    df_por_usuario = df.groupby('usuario').sum().sort_values('balance')
    output = []
    print("#### ", datetime.today().strftime("%Y/%m/%d %H:%M:%S"), " ####")
    for i, row in df_por_usuario.iterrows():
        tabulaciones_post_nombre = " \t==> \t" if len(row.name) > 5 else " \t\t==> \t"
        output.append(row.name + tabulaciones_post_nombre + '{:,} €'.format(row["balance"]).replace(',', '.'))
        print(row.name, tabulaciones_post_nombre, '{:,} €'.format(row["balance"]).replace(',', '.'))

    return output

def get_balances():
    movs = get_movs()
    df = pd.DataFrame.from_records([m.to_dict() for m in movs])
    df['balance'] = df['balance'].astype('int64')
    df_por_usuario = df.groupby('usuario').sum().sort_values('balance')
    return df_por_usuario

def get_liga_y_balances():
    balances = get_balances()
    liga = get_liga()
    liga_y_balances = balances.join(liga.set_index('usuario'), on='usuario')
    liga_y_balances['equipo_mas_saldo'] = liga_y_balances['balance'] + liga_y_balances['valor_equipo']
    liga_y_balances['dinero_generado'] = liga_y_balances['equipo_mas_saldo'] - bw_config.valor_total

    liga_y_balances['balance'] = liga_y_balances['balance'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['valor_equipo'] = liga_y_balances['valor_equipo'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['equipo_mas_saldo'] = liga_y_balances['equipo_mas_saldo'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['dinero_generado'] = liga_y_balances['dinero_generado'].astype(float).map('{:,.0f} €'.format)

    liga_y_balances = liga_y_balances.sort_values(by='pts', ascending=False)

    return liga_y_balances






