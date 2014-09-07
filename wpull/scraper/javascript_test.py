import os.path
import shutil
import unittest

from wpull.body import Body
from wpull.http.request import Request, Response
from wpull.scraper.html import HTMLScraper
from wpull.scraper.javascript import JavaScriptScraper
import wpull.util


ROOT_PATH = os.path.join(os.path.dirname(__file__), '..')


class TestJavascript(unittest.TestCase):
    def test_javascript_scraper(self):
        scraper = JavaScriptScraper()
        request = Request('http://example.com/script.js')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            html_file_path = os.path.join(ROOT_PATH,
                                          'testing', 'samples', 'script.js')
            with open(html_file_path, 'rb') as in_file:
                shutil.copyfileobj(in_file, response.body)

        scrape_info = scraper.scrape(request, response)
        inline_urls = scrape_info['inline_urls']
        linked_urls = scrape_info['linked_urls']

        self.assertEqual({
            'http://example.com/script_variable.png',
        },
            inline_urls
        )
        self.assertEqual({
            'http://example.com/document_write.html',
            'http://example.com/http_document_write.html',
            'http://example.com/http_document_write2.html',
            'http://example.com/http document write.html',
            'http://example.com/script_variable.html',
            'http://example.com/http_script_variable.html',
            'https://example.com/https_script_variable.html',
            'ftp://example.com/ftp_script_variable.html',
            'http://example.com/end_dir_script_variable/',
            'http://example.com/start_dir_script_variable',
            'http://example.com/../relative_dir_script_variable',
            'http://example.com/script_json.html',
            'http://example.com/http_script_json.html?a=b',
        },
            linked_urls
        )

    def test_javascript_heavy_inline_monstrosity(self):
        scraper = HTMLScraper()
        request = Request('http://example.com/')
        response = Response(200, 'OK')
        response.body = Body()

        with wpull.util.reset_file_offset(response.body):
            html_file_path = os.path.join(ROOT_PATH,
                                          'testing', 'samples',
                                          'twitchplayspokemonfirered.html')
            with open(html_file_path, 'rb') as in_file:
                shutil.copyfileobj(in_file, response.body)

        scrape_info = scraper.scrape(request, response)
        inline_urls = scrape_info['inline_urls']
        linked_urls = scrape_info['linked_urls']

        self.assertIn(
            'http://cdn.bulbagarden.net/upload/archive/a/a4/'
            '20090718115357%21195Quagsire.png',
            inline_urls
        )
        self.assertIn(
            'http://www.google.com/url?q=http%3A%2F%2Fwww.reddit.com%2F'
            'user%2FGoldenSandslash15&sa=D&sntz=1&'
            'usg=AFQjCNElFBxZYdNm5mWoRSncf5tbdIJQ-A',
            linked_urls
        )
