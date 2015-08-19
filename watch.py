try:
    from prettytable import PrettyTable
except ImportError as ie:
    import pip
    pip.main(['install', '-r', 'requirements.txt'])
    from prettytable import PrettyTable

import urllib2
import time
import ujson as json
import datetime
import os
import sys

from settings import config


class Watcher(object):
    def __init__(self):
        self.source = 'http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=l1'
        self.watchlist = self.build_portfolio()
        self.history_files = {}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        for f in self.history_files.values():
            f.close()

    def present(self):
        values = {
            'stock': [],
            'purchased_at': [],
            'shares': [],
            'purchased_price': [],
            'market_price': [],
            'orig_total_value': [],
            'gross_profit_per_share': [],
            'net_profit': [],
            'change_pct': [],

        }
        header_row = ['stock', 'purchased_at', 'shares', 'purchased_price', 'market_price', 'orig_total_value', 'gross_profit_per_share', 'net_profit', 'change_pct']
        table = PrettyTable(header_row)
        market_values = []
        for c in self.watchlist:
            for holding in c.get('holdings'):
                row = [
                    c.get('stock'),
                    holding.get('purchased').get('purchased_at'),
                    holding.get('purchased').get('shares'),
                    holding.get('purchased').get('purchased_price'),
                    c.get('history_live')[-1].get('price'),
                    holding.get('purchased').get('orig_total_value'),
                    holding.get('market').get('gross_profit_per_share'),
                    holding.get('market').get('net_profit'),
                    holding.get('market').get('change_pct'),
                ]
                table.add_row(row)
                values['stock'].append(c.get('stock'))
                values['purchased_at'].append(holding.get('purchased').get('purchased_at'))
                values['shares'].append(holding.get('purchased').get('shares'))
                values['purchased_price'].append(holding.get('purchased').get('purchased_price'))
                values['orig_total_value'].append(holding.get('purchased').get('orig_total_value'))
                values['market_price'].append(c.get('history_live')[-1].get('price'))
                values['gross_profit_per_share'].append(holding.get('market').get('gross_profit_per_share'))
                values['net_profit'].append(holding.get('market').get('net_profit'))
                values['change_pct'].append(holding.get('market').get('change_pct'))
                market_values.append(holding.get('market').get('market_total_value'))
            table.add_row(len(header_row)* ['.........',])
            # values = {k: v.append() for k,v in values.iteritems()}
        # "|  stock  | shares | purchased_price | purchased_at | orig_total_value | net_profit | market_price | gross_profit_per_share |   change_pct  |"
        total_market_value = sum(market_values)
        # for k, v in sorted(values.iteritems(), reverse=True):
        #     table.add_column(k, v)
        # table.add_row(['=======',]*len(header_row))
        summary = ['Summary', '-', sum(values['shares']), '-', '-', sum(values['orig_total_value']), total_market_value, sum(values['net_profit']), sum(values['change_pct'])]
        table.add_row(summary)
        os.system('clear')
        print table

    def watch(self):
        while True:
            for idx, c in enumerate(self.watchlist):
                try:
                    timestamp = time.time()
                    stat = urllib2.urlopen(self.source % c.get('stock')).read().strip()
                    self.watchlist[idx] = self.update_price_history(c, timestamp, float(stat))
                    self.watchlist[idx] = self.update_market_values_for_holdings(c)
                except Exception as ex:
                    print (ex.message)
                    sys.exit(1)
            self.present()
            time.sleep(config.get('update_frequency_sec'))

    def update_price_history(self, c, timestamp, price):
        monitored_at = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        if len(c['history_live']) >= config.get('history_live_window'):
            c['history_live'] = c['history_live'][1:]
        c['history_live'].append({'timestamp': monitored_at, 'price': price})
        self.store({'stock': c.get('stock'), 'timestamp': timestamp, 'price': price})
        return c

    def update_market_values_for_holdings(self, c):
        market_value_per_share = c['history_live'][-1].get('price')
        holdings = []
        for holding in c['holdings']:
            holding['market']['gross_profit_per_share'] = market_value_per_share - holding['purchased']['purchased_price']
            holding['market']['net_profit'] = ((market_value_per_share * holding['purchased']['shares']) - sum(config.get('fees'))) - (holding['purchased']['orig_total_value'] - sum(config.get('fees')))
            change = market_value_per_share - holding['purchased']['purchased_price']
            holding['market']['change_pct'] = (change / holding['purchased']['purchased_price']) * 100
            holding['market']['market_total_value'] = market_value_per_share * holding['purchased']['shares']
            holdings.append(holding)
        c['holdings'] = holdings
        return c


    def build_portfolio(self):
        portfolio_data = json.load(open(config.get('paths').get('portfolio_file_path'), 'r'))

        portfolio = []
        for stock in portfolio_data:
            portfolio.append({
                'stock': stock.get('code'),
                'history_live': [{'time': '', 'price': 0.00},],
                'holdings': map(self.stock_record, stock.get('holdings')),
                'announcement_dates': {},
                'news': {},
            })
        return portfolio

    def stock_record(self, record):
        return {
            'purchased': {
                'shares': record.get('shares'),
                'purchased_price': record.get('price'),
                'orig_total_value': record.get('shares') * record.get('price'),
                'purchased_at': record.get('purchased_at'),
            },
            'market': {
                'market_total_value': 0.00,
                'gross_profit_per_share': 0.00,
                'net_profit': 0.00,
                'change_pct': 0.00,
            },
        }

    def store(self, record):
        if config.get('history_tracking_enabled'):
            log_file = self.get_a_log_file(record.get('stock'))
            log_file.write('%s\n' % json.dumps(record))

    def get_a_log_file(self, stock):
        if stock in self.history_files:
            return self.history_files.get(stock)
        self.history_files[stock] = open(os.path.join(config.get('paths').get('historical_dir_path'), '%s.log' % stock), 'a')
        return self.history_files.get(stock)


if __name__ == '__main__':
    with Watcher() as watcher:
        watcher.watch()
