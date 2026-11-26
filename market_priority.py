"""Rank countries from the user's own AdSense country report; never guess RPM."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import main


def rank(path, minimum=1000):
    totals = {}
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'Country','PageViews','EstimatedEarnings'}.issubset(reader.fieldnames or []):
            raise ValueError('Expected Country,PageViews,EstimatedEarnings headers')
        for row in reader:
            country = main.COUNTRY_NAMES.get((row.get('Country') or '').strip().casefold())
            if not country:
                continue
            try:
                views = int(row['PageViews'])
                earnings = Decimal(row['EstimatedEarnings'])
                if views <= 0 or not earnings.is_finite() or earnings < 0:
                    continue
            except (ValueError, TypeError, InvalidOperation):
                continue
            oldv, olde = totals.get(country, (0,Decimal(0)))
            totals[country] = (oldv+views,olde+earnings)
    result = []
    for country in main.COUNTRIES:
        views, earnings = totals.get(country,(0,Decimal(0)))
        rpm = earnings*1000/views if views else None
        result.append((country,views,rpm,'sufficient' if views >= minimum else 'insufficient' if views else 'no data'))
    return sorted(result,key=lambda x:(x[3]!='sufficient',-(x[2] or Decimal(0)),x[0]))


def run():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv',type=Path)
    p.add_argument('--min-views',type=int,default=1000)
    args=p.parse_args()
    if args.min_views<1:
        p.error('--min-views must be positive')
    for country,views,rpm,state in rank(args.csv,args.min_views):
        value = f'{rpm:.2f}' if rpm is not None else 'N/A'
        print(f'{country:25} {views:10} {value:>10} {state}')

if __name__=='__main__':
    run()
