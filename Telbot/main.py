import os

import pymongo
from datetime import datetime, timedelta
import aiogram
import json
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
conn = pymongo.MongoClient('mongodb://localhost:27017/')
db = conn['test']


def get_env():
    dotenv_path = os.path.join(os.path.dirname('./'), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

get_env()

bot = aiogram.Bot(token=os.getenv('bot'))
dp = aiogram.Dispatcher(bot)
fields = ['dt_from', 'dt_upto', 'group_type']
groups_1 = {
    'month': relativedelta(months=1),
    'day': timedelta(days=1),
    'hour': timedelta(hours=1),
    'week': timedelta(weeks=1)
}
groups = {
    'month': {
        'month': '$month',
        'year': '$year'
    },
    'day': {
        'month': '$month',
        'year': '$year',
        'day': '$dayOfMonth'
    },
    'week': {
        'isoWeekYear': '$year',
        'isoWeek': '$week'
    },
    'hour': {
        'month': '$month',
        'year': '$year',
        'day': '$dayOfMonth',
        'hour': '$hour'
    }
}


@dp.message_handler(content_types='text')
async def get_mess(message: aiogram.types.Message):
    try:
        data = json.loads(message.text)
        assert all(map(lambda f: f in data, fields))
        assert any(map(lambda f: f in data.values(), groups))
        datetime.fromisoformat(data['dt_from'])
        datetime.fromisoformat(data['dt_upto'])
    except:
        await bot.send_message(message.chat.id, 'Not correct format')
        return
    init = dict()
    start = datetime.fromisoformat(data['dt_from'])
    end = datetime.fromisoformat(data['dt_upto'])
    s = datetime.fromisoformat(data['dt_from'])
    while s <= end:
        init[s.isoformat()] = 0
        s += groups_1[data['group_type']]
    q = db['db-dump'].aggregate(pipeline=[
        {
            "$match":
                {
                    "dt":
                        {
                            "$gte": start,
                            "$lte": end
                        }
                }
        },
        {
            "$project":
                {
                    **{k: {v: '$dt'} for k, v in groups[data['group_type']].items()},
                    "value": 1
                }
        },
        {
            "$group":
                {
                    "_id": {k: '$' + k for k in groups[data['group_type']]},
                    "count": {"$sum": "$value"}
                }
        },
        {
            '$addFields':
                {
                    'date': {'$dateFromParts': {k: '$_id.' + k for k in groups[data['group_type']]}}
                }
        },
        {
            '$sort':
                {
                    '_id': 1
                }
        }
    ])
    ex = {
        'dataset': [],
        'labels': []
    }
    for x in q:
        init[x['date'].isoformat()] += x['count']
    res = {
        'dataset': list(init.values()),
        'labels': list(init)
    }
    await bot.send_message(message.chat.id, json.dumps(res))

if __name__ == '__main__':
    aiogram.executor.start_polling(dp, skip_updates=True)
