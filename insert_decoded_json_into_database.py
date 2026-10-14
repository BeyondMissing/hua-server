import json
import pymysql


def parse(field, cate=1):
    if field is None or field == '':
        return "NULL" if cate == 1 else ""
    else:
        return field


def dry_search(json_data):
    range_list = [
        (100000, 190000),
        (200000, 201000),
        (300000, 301000),
        (400000, 401000),
        (500000, 501000),
        (600000, 601000),
        (700000, 701000),
        (800000, 801000),
        (900000, 901000),
        (1000000, 1001000),
        (1100000, 1101000),
        (1200000, 1201000),
        (1300000, 1301000),
        (1400000, 1401000),
        (1600000, 1601000),
        (1700000, 1701000),
        (1800000, 1801000),
        (1900000, 1901000)
    ]
    for rg in range_list:
        for idx in range(*rg):
            d = json_data.get(str(idx), None)
            if d is None:
                continue
            json_data.pop(str(idx))
    print(json_data)


def insert_type_cloth(conn, cursor, json_data):
    sql = "INSERT INTO type_clothes VALUES ({}, '{}', {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {});"
    for idx in range(100000, 110000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], int(d['Sex']), int(d['ClothType']), parse(d['Level']),
            parse(d['VIP']), parse(d['Equivalent']), parse(d['EquivCnt']), parse(d['Style']), parse(d['Money_type']),
            parse(d['Suit']), parse(d['Ttype'], 2), parse(d['Source'], 2), parse(d['Price']), parse(d['Typenum']), parse(d['EquivCnt'])
        )
        try:
            cursor.execute(f_sql)
            conn.commit()
            print("Inserted {}".format(d['ID']))
        except Exception as e:
            print(f_sql)
        # json_data.pop(str(idx))


def insert_type_cloth_2026(conn, cursor, json_data):
    sql = "INSERT INTO type_clothes_2026 VALUES ({}, '{}', {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {});"
    for idx in range(100000, 190000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], int(d['Sex']), int(d['ClothType']), parse(d['Level']),
            parse(d['VIP']), parse(d['Equivalent']), parse(d['EquivCnt']), parse(d['Style']), parse(d['Money_type']),
            parse(d['Suit']), parse(d['Ttype'], 2), parse(d['Source'], 2)
        )
        try:
            cursor.execute(f_sql)
            conn.commit()
            print("Inserted {}".format(d['ID']))
        except Exception as e:
            print(f_sql)
            print(e)


def insert_type_seeds(conn, cursor, json_data):
    sql = "INSERT INTO type_seeds VALUES ({}, '{}', {}, {}, {}, {}, {}, {}, {}, '{}', '{}');"
    for idx in range(200000, 201000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['Level']), parse(d['Price']), parse(d['Exp']), parse(d['Time']),
            parse(d['Area']), parse(d['Source']), parse(d['Des']), parse(d['LoveWeather']), parse(d['Talk'])
        )
        print(f_sql)
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_home_props(conn, cursor, json_data):
    sql = "INSERT INTO type_home_props VALUES ({}, '{}', '{}', '{}', {}, {}, '{}', {}, {}, {}, {}, {}, {}, {}, {});"
    for idx in range(300000, 301000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        print(d)
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['Tips']),
            parse(d['UseForPlantIDs']),
            parse(d['ToolType']),
            parse(d['Level']),
            parse(d['Allows']),
            parse(d['Price']),
            parse(d['Times']),
            parse(d['AddwaterNum']),
            parse(d['AddnutritionNum']),
            parse(d['Equivalent']),
            parse(d['EquivCnt']),
            parse(d['buyNum']),
            parse(d['Source']),
        )
        print(f_sql)
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_houses(conn, cursor, json_data):
    sql = "INSERT INTO type_houses VALUES ({}, '{}', {}, {}, {}, {}, {}, {});"
    for idx in range(400000, 401000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['Level']),
            parse(d['Price']),
            parse(d['GardenType']),
            parse(d['Equivalent']),
            parse(d['EquivCnt']),
            parse(d['Source']),
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_house_goods(conn, cursor, json_data):
    sql = "INSERT INTO type_house_goods VALUES ({}, '{}', {}, {}, {}, {}, {}, {}, {}, {});"
    for idx in range(500000, 501000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['MusicType']), parse(d['Level']), parse(d['VIP']),
            parse(d['Equivalent']), parse(d['HouseType']), parse(d['VipLevel']), parse(d['Source']), parse(d['Price'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_cloth_icons(conn, cursor, json_data):
    sql = "INSERT INTO type_cloth_icons VALUES ({}, '{}', {}, {}, {}, {}, {});"
    for idx in range(600000, 601000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['ClothType']), parse(d['Typenum']), parse(d['Equivalent']), parse(d['EquivCnt']), parse(d['Source'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_flowers(conn, cursor, json_data):
    sql = "INSERT INTO type_flowers VALUES ({}, '{}', {}, {}, {}, {}, {}, {}, {}, '{}');"
    for idx in range(700000, 701000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['FlowerType']), parse(d['Color_Type']), parse(d['Color_Value']),
            parse(d['Map']), parse(d['Des']), parse(d['Sell']), parse(d['Hot']), parse(d['Talk'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_pet_supplies(conn, cursor, json_data):
    sql = "INSERT INTO type_pet_supplies VALUES ({}, '{}', {}, {}, '{}', {}, {}, {}, {}, {}, {}, {});"
    for idx in range(800000, 801000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['Price']),
            parse(d['Level']),
            parse(d['Grade']),
            parse(d['Energy']),
            parse(d['Hungry']),
            parse(d['Sanitary']),
            parse(d['Spirit']),
            parse(d['Equivalent']),
            parse(d['EquivCnt']),
            parse(d['Source']),
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_pots(conn, cursor, json_data):
    sql = "INSERT INTO type_pots VALUES ({}, '{}', {}, {}, {}, {}, {}, {});"
    for idx in range(900000, 901000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['Level']),
            parse(d['Price']),
            parse(d['Times']),
            parse(d['Equivalent']),
            parse(d['EquivCnt']),
            parse(d['Source']),
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_home_bg(conn, cursor, json_data):
    sql = "INSERT INTO type_home_bg VALUES ({}, '{}', {}, {}, {}, {});"
    for idx in range(1000000, 1001000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['EventX']),
            parse(d['EventY']),
            parse(d['VIP']),
            parse(d['Source']),
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_task_materials(conn, cursor, json_data):
    sql = "INSERT INTO type_task_materials VALUES ({}, '{}', {});"
    for idx in range(1100000, 1101000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['UseType'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_pollens(conn, cursor, json_data):
    sql = "INSERT INTO type_pollens VALUES ({}, '{}', {});"
    for idx in range(1300000, 1301000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['Area'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_bones(conn, cursor, json_data):
    sql = "INSERT INTO type_bones VALUES ({}, '{}', {});"
    for idx in range(1400000, 1401000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['Typenum'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_materials(conn, cursor, json_data):
    sql = "INSERT INTO type_materials VALUES ({}, '{}', {}, {});"
    for idx in range(1600000, 1601000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['Price']), parse(d['Source'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_activity_icons(conn, cursor, json_data):
    sql = "INSERT INTO type_activity_icons VALUES ({}, '{}', '{}');"
    for idx in range(1700000, 1701000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name'], parse(d['hide'])
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_home_goods(conn, cursor, json_data):
    sql = "INSERT INTO type_home_goods VALUES ({}, '{}', {}, {}, {}, {}, {});"
    for idx in range(1800000, 1801000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']),
            d['Name'],
            parse(d['ToolType']),
            parse(d['Price']),
            parse(d['Max']),
            parse(d['Vip']),
            parse(d['Source']),
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def insert_type_magics(conn, cursor, json_data):
    sql = "INSERT INTO type_magics VALUES ({}, '{}');"
    for idx in range(1900000, 1901000):
        d = json_data.get(str(idx), None)
        if d is None:
            continue
        f_sql = sql.format(
            int(d['ID']), d['Name']
        )
        cursor.execute(f_sql)
        conn.commit()
        print("Inserted {}".format(d['ID']))


def main():
    with open("E:\\AS3Projects\\hua_scripts\\scripts_2013\work\\itemXmlData_2013.json", 'rt', encoding="UTF-8") as f:
        json_data = json.load(f)
        conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", passwd="root", db="hua_2013")
        cursor = conn.cursor()
        # insert_type_cloth(conn, cursor, json_data)
        dry_search(json_data)


main()
