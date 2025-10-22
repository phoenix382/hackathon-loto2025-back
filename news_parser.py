import feedparser
from datetime import datetime
import time


def get_rss_news(num_news=1):
    """
    Собирает указанное количество последних новостей из RSS-каналов

    Args:
        num_news (int): Количество последних новостей с каждого источника (по умолчанию 1)

    Returns:
        list: Массив словарей с новостями в формате:
              [
                  {
                      'source': 'Название источника',
                      'title': 'Заголовок новости',
                      'author': 'Автор (если есть)',
                      'date': 'Дата публикации',
                      'link': 'Ссылка на новость'
                  },
                  ...
              ]
    """
    rss_feeds = [
        {
            'name': 'АиФ Адыгея',
            'url': 'https://adigea.aif.ru/rss/googlearticles'
        },
        {
            'name': 'РИА Новости',
            'url': 'https://ria.ru/export/rss2/index.xml'
        },
        {
            'name': 'Правительство России',
            'url': 'http://government.ru/en/all/rss/'
        },
        {
            'name': 'ТАСС',
            'url': 'https://tass.com/rss/v2.xml'
        }
    ]

    all_news = []

    for feed_info in rss_feeds:
        try:
            # Парсим RSS-ленту
            feed = feedparser.parse(feed_info['url'])

            # Пропускаем если есть ошибки или нет новостей
            if feed.bozo and feed.bozo_exception or not feed.entries:
                continue

            # Берем N последних новостей
            for entry in feed.entries[:num_news]:
                # Обрабатываем дату
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    news_date = datetime(*entry.published_parsed[:6])
                    formatted_date = news_date.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(entry, 'published'):
                    formatted_date = entry.published
                else:
                    formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Получаем автора
                author = get_author_from_entry(entry, feed_info['name'])

                news_item = {
                    'source': feed_info['name'],
                    'title': entry.get('title', ''),
                    'author': author,
                    'date': formatted_date,
                    'link': entry.get('link', '')
                }

                all_news.append(news_item)

        except Exception:
            continue

        # Пауза между запросами
        time.sleep(0.5)

    return all_news


def get_author_from_entry(entry, default_author):
    """Извлекает автора из RSS записи"""
    author_fields = ['author', 'creator', 'dc:creator', 'dc:author']

    for field in author_fields:
        if hasattr(entry, field) and entry[field]:
            author = entry[field]
            # Очищаем автора
            if ',' in author:
                author = author.split(',')[0].strip()
            if '|' in author:
                author = author.split('|')[0].strip()
            return author

    return default_author