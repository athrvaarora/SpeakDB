import json
import datetime
from decimal import Decimal

# Custom JSON encoder for handling datetime and decimal objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        return super().default(o)