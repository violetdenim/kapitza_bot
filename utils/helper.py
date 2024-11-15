import datetime
def formatted_datetime():
    _dt = datetime.datetime.now()
    _date, _time = _dt.date(), _dt.time()
    return f"{_date.day}.{_date.month}.{_date.year} - {_time.hour}:{_time.minute}:{_time.second}"