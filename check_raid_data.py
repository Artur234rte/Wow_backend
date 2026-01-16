"""Скрипт для проверки данных по рейдам в БД"""
import asyncio
from sqlalchemy import select, func
from app.db.db import AsyncSessionLocal
from app.models.model import MetaBySpec
from app.agregator.constant import RAID


async def check_raid_data():
    async with AsyncSessionLocal() as session:
        print("=== Проверка данных по рейдам ===\n")

        # Проверка общего количества записей
        total_stmt = select(func.count()).select_from(MetaBySpec)
        total_result = await session.execute(total_stmt)
        total_count = total_result.scalar()
        print(f"Всего записей в meta_by_spec: {total_count}\n")

        # Проверка данных по рейдам (key=None)
        raid_stmt = (
            select(
                MetaBySpec.encounter_id,
                MetaBySpec.key,
                func.count().label('count')
            )
            .where(MetaBySpec.key.is_(None))
            .group_by(MetaBySpec.encounter_id, MetaBySpec.key)
            .order_by(MetaBySpec.encounter_id)
        )
        raid_result = await session.execute(raid_stmt)
        raid_rows = raid_result.all()

        print("Данные с key=NULL (должны быть рейды):")
        if raid_rows:
            for row in raid_rows:
                raid_name = RAID.get(row.encounter_id, "Неизвестный рейд")
                print(f"  Encounter ID: {row.encounter_id} ({raid_name}), key: {row.key}, записей: {row.count}")
        else:
            print("  НЕТ ДАННЫХ С key=NULL!")

        print("\n" + "="*50 + "\n")

        # Проверка всех encounter_id и их key
        all_enc_stmt = (
            select(
                MetaBySpec.encounter_id,
                MetaBySpec.key,
                func.count().label('count')
            )
            .group_by(MetaBySpec.encounter_id, MetaBySpec.key)
            .order_by(MetaBySpec.encounter_id, MetaBySpec.key)
        )
        all_enc_result = await session.execute(all_enc_stmt)
        all_enc_rows = all_enc_result.all()

        print("Все encounter_id в БД:")
        for row in all_enc_rows:
            raid_name = RAID.get(row.encounter_id, "M+ подземелье")
            print(f"  Encounter ID: {row.encounter_id} ({raid_name}), key: '{row.key}', записей: {row.count}")

        print("\n" + "="*50 + "\n")

        # Тестовый запрос как в meta_crud.py для рейда
        test_encounter_id = 2902  # Ulgrax the Devourer
        test_spec_type = "dps"

        print(f"Тестовый запрос для рейда {test_encounter_id} (Ulgrax the Devourer), spec_type={test_spec_type}:")
        test_stmt = (
            select(MetaBySpec)
            .where(
                MetaBySpec.encounter_id == test_encounter_id,
                MetaBySpec.spec_type == test_spec_type,
                MetaBySpec.key.is_(None)
            )
            .order_by(MetaBySpec.meta.desc())
        )
        test_result = await session.execute(test_stmt)
        test_rows = test_result.scalars().all()

        if test_rows:
            print(f"  Найдено записей: {len(test_rows)}")
            print("  Первые 5 результатов:")
            for i, row in enumerate(test_rows[:5], 1):
                print(f"    {i}. {row.class_name} - {row.spec}, meta: {row.meta}, dps: {row.average_dps}")
        else:
            print("  НЕТ ДАННЫХ ДЛЯ ЭТОГО ЗАПРОСА!")

            # Проверим, есть ли вообще данные для этого encounter_id
            check_stmt = (
                select(MetaBySpec.key, func.count().label('count'))
                .where(MetaBySpec.encounter_id == test_encounter_id)
                .group_by(MetaBySpec.key)
            )
            check_result = await session.execute(check_stmt)
            check_rows = check_result.all()

            if check_rows:
                print(f"\n  Но есть данные для encounter_id={test_encounter_id} с другими ключами:")
                for row in check_rows:
                    print(f"    key: '{row.key}', записей: {row.count}")
            else:
                print(f"\n  Вообще нет данных для encounter_id={test_encounter_id}!")


if __name__ == "__main__":
    asyncio.run(check_raid_data())
