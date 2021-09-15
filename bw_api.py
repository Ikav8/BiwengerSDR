import pandas as pd
import requests
from datetime import datetime
import config as bw_config
import time

class movimiento:
    def __init__(self, usuario, balance, detalles, jugador_id=-1, tipo='?', fecha=datetime.today(), valor_jugador=0, rendimiento=0):
        self.usuario = usuario
        self.jugador_id=jugador_id
        self.balance = int(balance)
        self.detalles = detalles
        self.tipo = tipo
        self.fecha = fecha
        self.valor_jugador = valor_jugador
        self.rendimiento = rendimiento

    def __str__(self):
        signo = '+' if int(self.balance) > 0 else '-'
        return ("[" + signo + "] " + self.usuario + " [ " + '{:,} €'.format(self.balance).replace(',', '.') +
                " ] < " + self.tipo + " > (" + self.detalles + ") (" +
                '{:,} €'.format(self.valor_jugador).replace(',', '.') + ") (^ " +
                '{:,} €'.format(self.rendimiento).replace(',', '.') + ") {" + str(self.fecha) + "}")

    def __repr__(self):
        signo = '+' if self.balance > 0 else '-'
        return ("[" + signo + "] " + self.usuario + " [ " + '{:,} €'.format(self.balance).replace(',', '.') +
                " ] < " + self.tipo + " > (" + self.detalles + ") (" +
                '{:,} €'.format(self.valor_jugador).replace(',', '.') + ") (^ " +
                '{:,} €'.format(self.rendimiento).replace(',', '.') + ") {" + str(self.fecha) + "}")

    def to_dict(self):
        return {
            'usuario' : self.usuario,
            'balance' : self.balance,
            'tipo' : self.tipo,
            'fecha' : self.fecha,
            'detalles' : self.detalles,
            'jugador_id': self.jugador_id,
            'valor_jugador' : self.valor_jugador,
            'rendimiento' : self.rendimiento
        }

ids_usuarios = bw_config.IDS_USUARIOS

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
        jugador_posicion_texto = posiciones.get(jugador.get('position'))
        jugador_info = jugador_nombre + " [" + jugador_posicion_texto + "]"
        jugadores_dict[jugador_id] = jugador_info

    return jugadores_dict


def get_jugadores_info():
    jugadores = get_jugadores()
    mega_lista_jugador_fecha_valor = []
    for jugador_id, jugador_nombre in jugadores.items():

        url_jugador_precio = "https://cf.biwenger.com/api/v2/players/la-liga/" + str(jugador_id) + \
                             "?lang=es&fields=*%2Cprices"
        r_jugador_precio = requests.get(url=url_jugador_precio)
        r_jugador_precio_json = r_jugador_precio.json()
        r_jugador_precio_json_data = r_jugador_precio_json.get('data', -1)

        if r_jugador_precio_json_data != -1:
            for fecha_i in r_jugador_precio_json_data['prices']:
                fecha = fecha_i[0]
                precio = fecha_i[1]
                if fecha <= 210801:
                    continue
                mega_lista_jugador_fecha_valor.append(
                    [int(jugador_id), jugador_nombre, datetime.strptime(str(fecha), '%y%m%d'), precio]
                )

    jugadores_con_info_df = pd.DataFrame(mega_lista_jugador_fecha_valor, columns=['jugador_id', 'jugador_nombre', 'fecha', 'precio'])

    return jugadores_con_info_df


def get_movs(pandas=False):

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

        fecha_bloque = int(data_item_bloque['date'])
        fecha_bloque_time = time.localtime(fecha_bloque)
        fecha_bloque_datetime = datetime.fromtimestamp(time.mktime(fecha_bloque_time))

        # transfer -- usuario -> usuario // usuario -> mercado
        if data_item_bloque['type'] == 'transfer':
            for transfer_item in data_item_bloque['content']:
                # from #
                id_usuario_from = str(transfer_item['from']['id'])
                nombre_usuario_from = ids_usuarios[id_usuario_from]
                balance = transfer_item['amount']
                jugador_id = transfer_item['player']
                jugador_info = lista_jugadores.get(str(jugador_id), '')
                movs.append(
                    movimiento(usuario=nombre_usuario_from,
                               balance=balance,
                               detalles=nombre_usuario_from + " vende a " + jugador_info,
                               fecha=fecha_bloque_datetime,
                               tipo='TRANSFER',
                               jugador_id=jugador_id)
                )

                # to ? #
                id_usuario_to = transfer_item.get('to', 'ERROR')
                if id_usuario_to != 'ERROR':
                    nombre_usuario_to = ids_usuarios[str(id_usuario_to['id'])]
                    movs.append(
                        movimiento(usuario=nombre_usuario_to,
                                   balance=balance * -1,
                                   detalles=nombre_usuario_to + " ficha a " + jugador_info,
                                   fecha=fecha_bloque_datetime,
                                   tipo='TRANSFER',
                                   jugador_id=jugador_id)
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
                               detalles=nombre_usuario_to + " ficha a " + str(jugador_info),
                               fecha=fecha_bloque_datetime,
                               tipo='MARKET',
                               jugador_id=jugador_id)
                )

        # roundFinished
        if data_item_bloque['type'] == 'roundFinished':
            nombre_jornada = data_item_bloque.get('content').get('round').get('name')
            resultados = data_item_bloque['content']['results']
            for resultado in resultados:
                user_id = str(resultado['user']['id'])
                user_nombre = ids_usuarios[user_id]
                dinero = resultado.get('bonus', 0)
                movs.append(
                    movimiento(usuario=user_nombre,
                               balance=dinero,
                               detalles=nombre_jornada,
                               fecha=fecha_bloque_datetime,
                               tipo='ROUNDFINISHED')
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
                               detalles=detalles,
                               fecha=fecha_bloque_datetime,
                               tipo='LOAN',
                               jugador_id=jugador_id)
                )
                movs.append(
                    movimiento(usuario=nombre_usuario_to,
                               balance=dinero * -1,
                               detalles=detalles,
                               fecha=fecha_bloque_datetime,
                               tipo='LOAN',
                               jugador_id=jugador_id)
                )

        # loanReturn (cesion a posteriori)
        if data_item_bloque['type'] == 'loanReturn':
            for loan_item in data_item_bloque['content']:

                dinero = loan_item.get('refund', 'NO REFUND')
                if dinero == 'NO REFUND':
                    continue

                id_usuario_from = str(loan_item['from']['id'])
                nombre_usuario_from = ids_usuarios[id_usuario_from]

                id_usuario_to = str(loan_item['to']['id'])
                nombre_usuario_to = ids_usuarios[id_usuario_to]

                jugador_id = loan_item['player']
                jugador_info = lista_jugadores.get(str(jugador_id))
                detalles = nombre_usuario_from + " devuelve a " + nombre_usuario_to + " a " + jugador_info
                movs.append(
                    movimiento(usuario=nombre_usuario_from,
                               balance=dinero,
                               detalles=detalles,
                               fecha=fecha_bloque_datetime,
                               tipo='LOAN RETURN',
                               jugador_id=jugador_id)
                )
                movs.append(
                    movimiento(usuario=nombre_usuario_to,
                               balance=dinero * -1,
                               detalles=detalles,
                               fecha=fecha_bloque_datetime,
                               tipo='LOAN RETURN',
                               jugador_id=jugador_id)
                )

        # bonus (lloros)
        if data_item_bloque['type'] == 'bonus':
            for bonus_item in data_item_bloque['content']:
                id_usuario = str(bonus_item['user']['id'])
                nombre_usuario = ids_usuarios[id_usuario]
                dinero = bonus_item['amount']

                detalles = nombre_usuario + " llora y recibe " + '{:,} €'.format(dinero).replace(',', '.')
                movs.append(
                    movimiento(usuario=nombre_usuario,
                               balance=dinero,
                               detalles=detalles,
                               fecha=fecha_bloque_datetime,
                               tipo='BONUS')
                )

    output = movs + bw_config.MOVS_INICIALES

    if pandas:
        output = pd.DataFrame.from_records([m.to_dict() for m in movs])

    return output


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
    liga_y_balances['puja_maxima'] = liga_y_balances['valor_equipo'] * 0.25 + liga_y_balances['balance']

    liga_y_balances['balance'] = liga_y_balances['balance'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['valor_equipo'] = liga_y_balances['valor_equipo'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['puja_maxima'] = liga_y_balances['puja_maxima'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['equipo_mas_saldo'] = liga_y_balances['equipo_mas_saldo'].astype(float).map('{:,.0f} €'.format)
    liga_y_balances['dinero_generado'] = liga_y_balances['dinero_generado'].astype(float).map('{:,.0f} €'.format)

    liga_y_balances = liga_y_balances.sort_values(by='pts', ascending=False)

    return liga_y_balances






