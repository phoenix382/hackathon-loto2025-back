import requests
from typing import Dict, List

class OpenMeteoWeatherParser:
    def __init__(self):
        self.continent_coordinates = {
            'Европа': [
                {'city': 'Лондон', 'lat': 51.5074, 'lon': -0.1278},
                {'city': 'Париж', 'lat': 48.8566, 'lon': 2.3522},
                {'city': 'Берлин', 'lat': 52.5200, 'lon': 13.4050},
                {'city': 'Москва', 'lat': 55.7558, 'lon': 37.6173},
                {'city': 'Рим', 'lat': 41.9028, 'lon': 12.4964}
            ],
            'Азия': [
                {'city': 'Токио', 'lat': 35.6762, 'lon': 139.6503},
                {'city': 'Пекин', 'lat': 39.9042, 'lon': 116.4074},
                {'city': 'Сеул', 'lat': 37.5665, 'lon': 126.9780},
                {'city': 'Дели', 'lat': 28.6139, 'lon': 77.2090},
                {'city': 'Бангкок', 'lat': 13.7563, 'lon': 100.5018}
            ],
            'Северная Америка': [
                {'city': 'Нью-Йорк', 'lat': 40.7128, 'lon': -74.0060},
                {'city': 'Лос-Анджелес', 'lat': 34.0522, 'lon': -118.2437},
                {'city': 'Чикаго', 'lat': 41.8781, 'lon': -87.6298},
                {'city': 'Торонто', 'lat': 43.6532, 'lon': -79.3832},
                {'city': 'Мехико', 'lat': 19.4326, 'lon': -99.1332}
            ],
            'Южная Америка': [
                {'city': 'Буэнос-Айрес', 'lat': -34.6037, 'lon': -58.3816},
                {'city': 'Сан-Паулу', 'lat': -23.5505, 'lon': -46.6333},
                {'city': 'Лима', 'lat': -12.0464, 'lon': -77.0428},
                {'city': 'Богота', 'lat': 4.7110, 'lon': -74.0721},
                {'city': 'Сантьяго', 'lat': -33.4489, 'lon': -70.6693}
            ],
            'Африка': [
                {'city': 'Каир', 'lat': 30.0444, 'lon': 31.2357},
                {'city': 'Лагос', 'lat': 6.5244, 'lon': 3.3792},
                {'city': 'Йоханнесбург', 'lat': -26.2041, 'lon': 28.0473},
                {'city': 'Найроби', 'lat': -1.2864, 'lon': 36.8172},
                {'city': 'Кейптаун', 'lat': -33.9249, 'lon': 18.4241}
            ],
            'Австралия и Океания': [
                {'city': 'Сидней', 'lat': -33.8688, 'lon': 151.2093},
                {'city': 'Мельбурн', 'lat': -37.8136, 'lon': 144.9631},
                {'city': 'Окленд', 'lat': -36.8509, 'lon': 174.7645},
                {'city': 'Брисбен', 'lat': -27.4698, 'lon': 153.0251},
                {'city': 'Перт', 'lat': -31.9505, 'lon': 115.8605}
            ]
        }
        
        self.weather_codes = {
            0: 'ясно', 1: 'преимущественно ясно', 2: 'переменная облачность', 3: 'пасмурно',
            45: 'туман', 48: 'туман', 51: 'легкая морось', 53: 'умеренная морось', 
            55: 'сильная морось', 56: 'легкая ледяная морось', 57: 'сильная ледяная морось',
            61: 'небольшой дождь', 63: 'умеренный дождь', 65: 'сильный дождь',
            66: 'легкий ледяной дождь', 67: 'сильный ледяной дождь',
            71: 'небольшой снег', 73: 'умеренный снег', 75: 'сильный снег',
            77: 'снежные зерна', 80: 'небольшие ливни', 81: 'умеренные ливни', 82: 'сильные ливни',
            85: 'небольшие снежные ливни', 86: 'сильные снежные ливни',
            95: 'гроза', 96: 'гроза с мелким градом', 99: 'гроза с крупным градом'
        }

    def _get_weather_data(self, lat: float, lon: float, city: str) -> Dict:
        """Получает полные данные о погоде для одной локации"""
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,pressure_msl,precipitation,rain,showers,"
                f"snowfall,wind_speed_10m,wind_direction_10m,cloud_cover,weather_code"
                f"&timezone=auto"
            )
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()['current']
                return {
                    'city': city,
                    'temperature': data.get('temperature_2m', 0),
                    'humidity': data.get('relative_humidity_2m', 0),
                    'pressure': data.get('pressure_msl', 0),
                    'precipitation': data.get('precipitation', 0),
                    'rain': data.get('rain', 0),
                    'showers': data.get('showers', 0),
                    'snowfall': data.get('snowfall', 0),
                    'wind_speed': data.get('wind_speed_10m', 0),
                    'wind_direction': data.get('wind_direction_10m', 0),
                    'cloud_cover': data.get('cloud_cover', 0),
                    'weather_code': data.get('weather_code', 0),
                    'weather_description': self.weather_codes.get(data.get('weather_code', 0), 'неизвестно')
                }
        except Exception as e:
            print(f"Ошибка получения данных для {city}: {e}")
            return None

    def _calculate_averages(self, weather_data: List[Dict]) -> Dict:
        """Вычисляет средние значения и агрегированные данные для континента"""
        if not weather_data:
            return None
            
        # Основные средние значения
        avg_temperature = round(sum(d['temperature'] for d in weather_data) / len(weather_data), 1)
        avg_humidity = round(sum(d['humidity'] for d in weather_data) / len(weather_data), 1)
        avg_pressure = round(sum(d['pressure'] for d in weather_data) / len(weather_data), 1)
        avg_wind_speed = round(sum(d['wind_speed'] for d in weather_data) / len(weather_data), 1)
        avg_cloud_cover = round(sum(d['cloud_cover'] for d in weather_data) / len(weather_data), 1)
        
        # Суммарные осадки
        total_precipitation = round(sum(d['precipitation'] for d in weather_data), 1)
        total_rain = round(sum(d['rain'] for d in weather_data), 1)
        total_snowfall = round(sum(d['snowfall'] for d in weather_data), 1)
        
        # Наиболее частый тип погоды
        weather_descriptions = [d['weather_description'] for d in weather_data]
        common_weather = max(set(weather_descriptions), key=weather_descriptions.count)
        
        # Определение преобладающих условий
        rainy_cities = sum(1 for d in weather_data if d['precipitation'] > 0)
        snowy_cities = sum(1 for d in weather_data if d['snowfall'] > 0)
        cloudy_cities = sum(1 for d in weather_data if d['cloud_cover'] > 50)
        
        return {
            # Основные параметры
            'avg_temperature': avg_temperature,
            'avg_humidity': avg_humidity,
            'avg_pressure': avg_pressure,
            'avg_wind_speed': avg_wind_speed,
            'avg_cloud_cover': avg_cloud_cover,
            
            # Осадки
            'total_precipitation': total_precipitation,
            'total_rain': total_rain,
            'total_snowfall': total_snowfall,
            'precipitation_intensity': self._get_precipitation_intensity(total_precipitation),
            
            # Погодные условия
            'common_weather': common_weather,
            'rainy_cities_count': rainy_cities,
            'snowy_cities_count': snowy_cities,
            'cloudy_cities_count': cloudy_cities,
            
            # Статистика
            'cities_count': len(weather_data),
            'cities_analyzed': [d['city'] for d in weather_data]
        }

    def _get_precipitation_intensity(self, precipitation: float) -> str:
        """Определяет интенсивность осадков"""
        if precipitation == 0:
            return 'без осадков'
        elif precipitation < 2.5:
            return 'слабые осадки'
        elif precipitation < 7.5:
            return 'умеренные осадки'
        else:
            return 'сильные осадки'

    def get_continent_weather(self) -> Dict[str, Dict]:
        """
        Возвращает полные средние параметры погоды для каждого континента
        
        Returns:
            Dict с данными по континентам в формате:
            {
                'Европа': {
                    'avg_temperature': 15.5,
                    'avg_humidity': 65.2,
                    'avg_pressure': 1013.2,
                    'avg_wind_speed': 3.2,
                    'avg_cloud_cover': 45.1,
                    'total_precipitation': 2.1,
                    'total_rain': 1.8,
                    'total_snowfall': 0.3,
                    'precipitation_intensity': 'слабые осадки',
                    'common_weather': 'ясно',
                    'rainy_cities_count': 2,
                    'snowy_cities_count': 1,
                    'cloudy_cities_count': 2,
                    'cities_count': 5,
                    'cities_analyzed': ['Лондон', 'Париж', ...]
                },
                ...
            }
        """
        result = {}
        
        for continent, cities in self.continent_coordinates.items():
            continent_weather = []
            
            for city_data in cities:
                weather = self._get_weather_data(
                    city_data['lat'], 
                    city_data['lon'], 
                    city_data['city']
                )
                if weather:
                    continent_weather.append(weather)
            
            if continent_weather:
                result[continent] = self._calculate_averages(continent_weather)
        
        return result