import json
import datetime

# Custom JSON encoder for handling datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)