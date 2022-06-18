import sqlite3
import tkinter as tk
from tkinter import ttk

import scrapy
from bs4 import BeautifulSoup
from scrapy.crawler import CrawlerProcess


# Crawler
class ProgramSpider(scrapy.Spider):
    name = "programs"

    # cookies and headers added to be able to access btv website
    # or else it blocks the crawler
    # NOTE: change luckynumber from time to time or you will
    # be blocked from btv
    cookies = {
        'CookieOptIn': 'true',
        'luckynumber': '1326712231',
        'MpSession': '9ff31f05-36fd-4570-9cdc-e1800bf682fe',
    }

    headers = {
        'Pragma': 'no-cache',
        'DNT': '1',
        'Accept-Encoding': 'gzip, deflate, sdch, br',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'no-cache',
        'Referer': 'https://www.marktplaats.nl/cookiewall/?target=https%3A%2F%2Fwww.marktplaats.nl%2F',
        'Connection': 'keep-alive',
    }

    def start_requests(self):
        urls = [
            'https://nova.bg/schedule',
            'https://www.btv.bg/programata/'
        ]

        # delete and create table anew to prevent duplicate entries
        # NOTE: could use other methods to avoid duplication
        # but are more complex (outside of this course)
        cur.execute('DROP TABLE IF EXISTS programs')
        cur.execute('CREATE TABLE IF NOT EXISTS\
            programs (name text, time text, date text, tv_network text)')

        for url in urls:
            if url.find("nova") != -1:
                yield scrapy.Request(
                    url=url,
                    callback=self.get_urls_from_week_nova
                )
            elif url.find("btv") != -1:
                yield scrapy.Request(
                    url=url,
                    callback=self.get_urls_from_week_btv,
                    headers=self.headers,
                    cookies=self.cookies
                )

    # Different parsers for Nova and BTV as they have different page structure
    def get_urls_from_week_nova(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')

        a_links = soup.find_all(class_="gtm-TVProgramaDays-click", href=True)

        links = []
        for link in a_links:
            links.append(link['href'])

        for link in links:
            yield scrapy.Request(url=link, callback=self.parse_nova)

    def parse_nova(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')

        tv_network = "nova"

        shows = soup.find_all(class_="gtm-TVLiveBroadcasts-click")
        show_hours = soup.find_all(class_="timeline-hour")
        date = soup.find(class_="active-day").find(
            class_="gtm-TVProgramaDays-click",
            href=True
        )['href'][-6:-1]

        for (show, hour) in zip(shows, show_hours):
            save_to_db(show.contents[0], hour.contents[0], date, tv_network)

    def get_urls_from_week_btv(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')

        a_links = soup.find_all(class_="day-item")

        links = []
        for link in a_links:
            specific_day = link.find('a')['href']
            links.append(f'https://www.btv.bg{specific_day}')

        for link in links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_btv,
                headers=self.headers,
                cookies=self.cookies
            )

    def parse_btv(self, response):
        soup = BeautifulSoup(response.body, 'html.parser')

        tv_network = "btv"

        shows = soup.find_all(class_="schedule-item")
        date = soup.find(
            class_="is-today",
            href=True
        ).find(class_="date").contents[0]

        for show in shows:
            show_hour = show.find(class_="time").contents[0]
            show_name = show.find(class_="title").contents[0]

            save_to_db(show_name, show_hour, date, tv_network)


def save_to_db(name, hour, date, tv_network):
    cur.execute(
        "INSERT INTO programs VALUES (?, ?, ?, ?)",
        (name, hour, date, tv_network)
    )


# Button functions
def search_programme():
    tree.delete(*tree.get_children())

    for row in cur.execute(f'SELECT * FROM programs WHERE\
            name LIKE "%{command.get()}%"'):
        tree.insert('', tk.END, values=row)


def get_programmes():
    process.start()
    con.commit()


def list_programme():
    tree.delete(*tree.get_children())

    for row in cur.execute('SELECT * FROM programs'):
        tree.insert('', tk.END, values=row)


# DB setup
con = sqlite3.connect('db.sqlite')
cur = con.cursor()


# Crawler setup
process = CrawlerProcess()

process.crawl(ProgramSpider)


# Tkinter window setup
root = tk.Tk()
root.title('TV Programme browser')
root.geometry('800x600+50+50')


command_label = ttk.Label(root, text='Search programme:')
command_label.pack(ipady=5)

command = tk.StringVar()
command_entry = ttk.Entry(root, textvariable=command, width=50)
command_entry.pack(pady=10)

search_button = ttk.Button(
    root,
    text="search programme",
    command=search_programme,
    width=50
)
search_button.pack(pady=20)

get_button = ttk.Button(
    root,
    text="get programmes",
    command=get_programmes,
    width=50
)
get_button.pack(pady=20)

list_button = ttk.Button(
    root,
    text="list programme",
    command=list_programme,
    width=50
)
list_button.pack(pady=20)


columns = ('show', 'time', 'date', 'tv_network')

tree = ttk.Treeview(root, columns=columns, show='headings')

tree.heading('show', text='Show')
tree.heading('time', text='Time')
tree.heading('date', text='Date')
tree.heading('tv_network', text='TV Network')

tree.pack(pady=10)

scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscroll=scrollbar.set)

# Start application
root.mainloop()
