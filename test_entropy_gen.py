# import sys
# sys.path.append('/content/NistRng')

def test_file(path):
    import nistrng
    import numpy as np

    # Читаем файл
    with open(path, 'r') as f:
        data = f.read().strip()

    sequence = np.array([int(bit) for bit in data if bit in '01'], dtype=int)

    from nistrng import check_eligibility_all_battery, run_all_battery, SP800_22R1A_BATTERY

    # Проверяем eligibility
    eligible_battery = check_eligibility_all_battery(sequence, SP800_22R1A_BATTERY)

    print("\nПроверка пригодности данных (eligibility):")
    eligible_count = sum(1 for eligible in eligible_battery.values() if eligible)
    print(f"Доступно тестов: {eligible_count}/{len(eligible_battery)}")

    # Запускаем тесты
    print("\n🔄 Запускаю тесты NIST... Это может занять несколько минут...")
    results = run_all_battery(sequence, eligible_battery, SP800_22R1A_BATTERY)

    # Выводим результаты
    print("\n" + "=" * 60)
    print("РЕАЛЬНЫЕ РЕЗУЛЬТАТЫ ТЕСТОВ NIST")
    print("=" * 60)

    passed_tests = 0
    total_tests = 0

    for result_tuple, name in zip(results, eligible_battery):
        if eligible_battery[name]:
            total_tests += 1

            # Распаковываем кортеж
            result_obj, index = result_tuple

            # Используем правильные атрибуты
            passed = result_obj.passed
            score = result_obj.score  # Это p-value

            status = "✅ PASS" if passed else "❌ FAIL"
            if passed:
                passed_tests += 1

            print(f"{name:.<50} {status} (p-value: {score:.6f})")

    print(f"\nИТОГ: {passed_tests}/{total_tests} тестов пройдено")

    # Оценка качества
    print(f"\n=== ОЦЕНКА КАЧЕСТВА ===")
    if passed_tests == total_tests:
        print("🎉 ОТЛИЧНО: Все тесты пройдены! Последовательность случайна.")
    elif passed_tests >= total_tests * 0.9:
        print("👍 ОЧЕНЬ ХОРОШО: Пройдено более 90% тестов")
    elif passed_tests >= total_tests * 0.8:
        print("👍 ХОРОШО: Пройдено более 80% тестов")
    elif passed_tests >= total_tests * 0.7:
        print("⚠️  УДОВЛЕТВОРИТЕЛЬНО: Пройдено более 70% тестов")
    else:
        print("❌ ПЛОХО: Меньше 70% тестов пройдено")

    print(f"Процент пройденных тестов: {passed_tests / total_tests * 100:.1f}%")


test_file('random_secure.txt')