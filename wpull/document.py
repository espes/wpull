import abc
import lxml.html
import re
import urllib.parse

import wpull.util


class BaseDocumentScraper(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def scrape(self, request, response):
        pass


class HTMLScraper(BaseDocumentScraper):
    ATTR_INLINE = 1
    ATTR_HTML = 2

    TAG_HANDLERS = {
        'a': 'url',
        'applet': 'url',
        'area': 'url',
        'base': 'base',
        'bgsound': 'url',
        'body': 'url',
        'embed': 'url',
        'fig': 'url',
        'form': 'form',
        'frame': 'url',
        'iframe': 'url',
        'img': 'url',
        'input': 'url',
        'link': 'link',
        'meta': 'meta',
        'object': 'url',
        'overlay': 'url',
        'script': 'url',
        'table': 'url',
        'td': 'url',
        'th': 'url',
    }

    TAG_ATTRIBUTES = {
        'a': {'href': ATTR_HTML},
        'applet': {'code': ATTR_INLINE},
        'area': {'href': ATTR_HTML},
        'bgsound': {'src': ATTR_INLINE},
        'body': {'background': ATTR_INLINE},
        'embed': {'href': ATTR_HTML, 'src': ATTR_INLINE | ATTR_HTML},
        'fig': {'src': ATTR_INLINE},
        'frame': {'src': ATTR_INLINE | ATTR_HTML},
        'iframe': {'src': ATTR_INLINE | ATTR_HTML},
        'img': {'href': ATTR_INLINE, 'lowsrc': ATTR_INLINE, 'src': ATTR_INLINE},
        'input': {'src': ATTR_INLINE},
        'layer': {'src': ATTR_INLINE | ATTR_HTML},
        'object': {'data': ATTR_INLINE},
        'overlay': {'src': ATTR_INLINE | ATTR_HTML},
        'script': {'src': ATTR_INLINE},
        'table': {'background': ATTR_INLINE},
        'td': {'background': ATTR_INLINE},
        'th': {'background': ATTR_INLINE},
    }

    def __init__(self, accepted=None, rejected=None):
        super().__init__()
        # TODO: accept/reject tags option

    def scrape(self, request, response):
        inline_urls = set()
        html_urls = set()
        base_url = request.url_info.url
        root = self._parse_document(response.body.content_file, base_url)

        self._scrape_links_by_lxml(root, inline_urls, html_urls, base_url)
        self._scrape_links_by_wget(root, inline_urls, html_urls, base_url)

        # TODO: discard html_urls if robots nofollow in meta
        return (inline_urls, html_urls)

    def _is_accepted(self, element_tag):
        # TODO:
        return True

    def _parse_document(self, content_file, base_url):
        with wpull.util.reset_file_offset(content_file):
            root = lxml.html.parse(content_file).getroot()

        self._make_links_absolute(root, base_url)

        return root

    def _make_links_absolute(self, root, base_url):
        self._make_links_absolute_monkey(root, base_url)
        root.make_links_absolute(base_url)

    def _make_links_absolute_monkey(self, root, base_url):
        # TODO: this might be a bug in lxml
        for element in root.iter('applet'):
            if 'codebase' in element.attrib:
                element_base_url = urllib.parse.urljoin(
                    base_url,
                    element.attrib['codebase'])
            else:
                element_base_url = base_url

            for attribute in ('code', 'src',):
                if attribute in element.attrib:
                    element.set(
                        attribute,
                        urllib.parse.urljoin(
                            element_base_url,
                            element.attrib[attribute])
                    )
            if 'archive' in element.attrib:
                for match in re.finditer(r'[^ ]+', element.get('archive')):
                    value = match.group(0)
                    value = urllib.parse.urljoin(element_base_url, value)
                    element.set('archive', value)

    def _scrape_links_by_lxml(self, root, inline_urls, html_urls, base_url):
        for element, attribute, url, pos in root.iterlinks():
            tag = element.tag

            if tag == 'form':
                continue

            if tag == 'link':
                if self._is_link_inline(element):
                    inline_urls.add(url)
                else:
                    html_urls.add(url)
                continue

            if self._is_inline(tag, attribute):
                inline_urls.add(url)
            if self._is_html_link(tag, attribute):
                html_urls.add(url)

        self._scrape_links_by_lxml_monkey(root, inline_urls, html_urls, base_url)

    def _scrape_links_by_lxml_monkey(self, root, inline_urls, html_urls,
    base_url):
        # TODO: is this a bug in lxml
        for element in root.iter('style'):
            for match in re.finditer(r"@import '(.*?)'", element.text):
                url = urllib.parse.urljoin(base_url, match.group(1))
                inline_urls.add(url)

    def _scrape_links_by_wget(self, root, inline_urls, html_urls, base_url):
        for element in root.iter():
            tag = element.tag
            handler = self.TAG_HANDLERS.get(tag)

            if handler == 'url':
                for attribute, url in element.attrib.items():
                    if self._is_inline(tag, attribute):
                        inline_urls.add(url)
                    if self._is_html_link(tag, attribute):
                        html_urls.add(url)
            elif handler == 'meta':
                if element.get('http-equiv', '').lower() == 'refresh':
                    content_value = element.get('content')
                    print(content_value)
                    match = re.search(
                            r'url=(.+)', content_value, re.IGNORECASE)
                    if match:
                        url = urllib.parse.urljoin(base_url, match.group(1))
                        html_urls.add(url)
            # Ignore form and link handlers because they are handled through
            # lxml and generic logic

    def _is_inline(self, tag, attribute):
        if tag in self.TAG_ATTRIBUTES \
        and attribute in self.TAG_ATTRIBUTES[tag]:
            attr_flags = self.TAG_ATTRIBUTES[tag][attribute]
            return attr_flags & self.ATTR_INLINE

        return attribute != 'href'

    def _is_html_link(self, tag, attribute):
        if tag in self.TAG_ATTRIBUTES \
        and attribute in self.TAG_ATTRIBUTES[tag]:
            attr_flags = self.TAG_ATTRIBUTES[tag][attribute]
            return attr_flags & self.ATTR_HTML

        return attribute == 'href'

    def _is_link_inline(self, element):
        assert element.tag == 'link'
        rel = element.get('rel')

        if 'stylesheet' in rel or 'icon' in rel:
            return True


class CSSScraper(BaseDocumentScraper):
    # TODO: scrape url()s
    pass


class BaseDocumentConverter(object, metaclass=abc.ABCMeta):
    pass


class LocalHTMLConverter(BaseDocumentConverter):
    # TODO: convert links to local
    pass
