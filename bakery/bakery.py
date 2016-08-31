#/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

__author__ = 'Johan Nilsson'
__version__ = '0.4.dev'
__license__ = 'MIT'

import sys
import pystache
import os
import shutil
import errno
import fnmatch
import markdown
import codecs
import re
import yaml
import hashlib
import threading
import time
import socket
import filecmp
import typogrify
import Image
import math
import copy
from unicodedata import normalize
from functools import partial

# Workaround for the "print is a keyword/function" Python 2/3 dilemma
# and a fallback for mod_wsgi (resticts stdout/err attribute access)
# From Bottle.
try:
    _stdout, _stderr = sys.stdout.write, sys.stderr.write
except IOError:
    _stdout = lambda x: sys.stdout.write(x)
    _stderr = lambda x: sys.stderr.write(x)


def mkdir_p(path):
    """ Create intermediate directories as required.
    """
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

# Helper to slugify paths.
# http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))


class TemplateView(pystache.TemplateSpec):
    pass


class Config(object):
    """ Configuration for the site to build. """
    paths = {
        'assets': u'assets',
        'layouts': u'layouts',
        'media': u'media',
        'pages': u'pages',
    }

    def __init__(self, path=None, **config):
        c = None
        if path is not None:
            with codecs.open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            c = yaml.load(content)
        if c is not None:
            c.update(config)
        else:
            c = config

        if config.get('no_compress'):
            c['compress'] = False

        self.site_context = c.get('site_context', {})
        self.media = c.get('media', {})
        self.compress = c.get('compress', False)
        self.source_dir = c.get('source_dir', None)
        self.build_dir = c.get('build_dir', None)
        self.production = c.get('production', False)
        self.pagination = c.get('pagination', {})

        self.site_context.update({'production': self.production})

        if self.source_dir is None:
            self.source_dir = os.getcwd()
        if self.build_dir is None:
            self.build_dir = os.getcwd() + '/_out'


class Loader(object):
    """ Content and context loader for resources.
    """
    def __init__(self, source=''):
        self.source = source

    def load(self, path):
        """ Return content and context from path.

        Return a tuple consisting of the content as a string and a dict
        representing the context extracted from a yaml front matter if 
        present in the content.
        """
        context = {}
        with codecs.open(self.source + path, 'r', encoding='utf-8') as f:
            content = f.read()
        result = re.search(r'^(---\s*\n.*?\n?)^(---\s*$\n?)', content, re.DOTALL|re.MULTILINE)
        if result:
            front_matter = result.group(1)
            context = yaml.load(front_matter)
            content = content[result.end(0):len(content)]
        return content, context


class Resource(object):
    """ Base resource
    """
    def __init__(self, config, source):
        self.config = config
        self.source = source

    def _clean_source(self):
        """ Clears the first directory from the destination path.
        """
        i = self.source.find(os.sep) + 1
        if i == 1:
            i = self.source[i:].find(os.sep) + 1
        return self.source[i:]

    @property
    def destination(self):
        return self._clean_source()
    # Alias url to destination
    url = destination

    @property
    def belongs_to(self):
        return os.path.basename(os.path.dirname(self.destination))

    @property
    def belongs_to_parent(self):
        root, last = os.path.split(os.path.dirname(self.destination))
        parent = os.path.basename(root)
        if parent == "":
            parent = None
        return parent


class PageResource(Resource):
    def __init__(self, config, source, context=None):
        super(PageResource, self).__init__(config, source)

        if not context:
            context = {}

        self.context = context
        self.id = hashlib.md5(self.source).hexdigest()
        self.layout_path = u'default.html'
        self.page_layout_path = None
        self.pager = None
        self.content = None
        self.rendered_content = None
        self.rendered_page = None

        l = Loader(source=config.source_dir)
        content, context = l.load(self.source)
        self.context.update(context)
        self.page_content = content

        if 'layout' in self.context:
            self.layout_path = self.context['layout']
        if 'page_layout' in self.context:
            self.page_layout_path = self.context['page_layout']

    def __getattr__(self, key):
        """
        Adds dynamic access of context attributes.
        """
        return self.context.get(key, '')

    def __repr__(self):
        return '<PageResource {0}>'.format(self.title)

    @property
    def layout(self):
        return self.config.source_dir + os.sep + self.config.paths['layouts'] + os.sep + self.layout_path

    @property
    def page_layout(self):
        return self.config.source_dir + os.sep + self.config.paths['layouts'] + os.sep + self.page_layout_path

    @property
    def title(self):
        return self.context.get('title', '')

    @property
    def destination(self):
        root, ext = os.path.splitext(self._clean_source())
        return root + u'.html'
    url = destination

    def should_build(self):
        """ Check if this resource should be built out to a html doc.
        """
        return self.context.get('build', True)

    def build(self):
        """ Build this resource using the passed renderer and optional context.
        """
        if self.pager is not None:
            self.context.update({u'pager': self.pager.to_dict()})

        dst = self.config.build_dir + os.sep + self.destination
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            mkdir_p(dst_dir)
        with codecs.open(dst, 'w', encoding='utf-8') as f:
            f.write(self.rendered_page)

    def render(self, renderer, site_context):
        view = TemplateView()
        if self.page_layout_path:
            view.template_rel_path = self.page_layout
        else:
            view.template = self.page_content
        part = renderer.render(view, self.context, site=site_context)
        part = markdown.markdown(part)
        part = typogrify.typogrify(part)
        page_context = {u'content': part}
        self.rendered_content = part
        page_context.update(self.context)

        view = TemplateView()
        view.template_rel_path = self.layout

        page = renderer.render(view, self.context, page=page_context, site=site_context)
        self.rendered_page = page


class MediaResource(Resource):
    """ A media resource

    This is a special type of resource that group images into collections based
    on the directory they placed in.
    """
    def __init__(self, config, source):
        super(MediaResource, self).__init__(config, source)
        self.source = self.source.replace(self.config.source_dir, '', 1)

    def __repr__(self):
        return '<MediaResource {0}>'.format(self.source)

    def get_image_url(self, size_name):
        root, ext = os.path.splitext(self.destination)
        path = slugify(root + u'-' + size_name) + ext
        return path 

    def create_image(self, name, size):
        path = self.get_image_url(name)
        if path.startswith(os.sep):
            path = path[1:]
        src = os.sep.join([self.config.source_dir, self.source])
        dst = os.sep.join([self.config.build_dir, path])
        dst_dir = os.path.dirname(dst)
        if not os.path.isdir(dst_dir):
            mkdir_p(dst_dir)
        if not os.path.isfile(dst):
            try:
                img = Image.open(src)
                img.thumbnail((
                    size.get('width'),
                    size.get('height')
                ), Image.ANTIALIAS)
                img.save(dst)
            except Exception, e:
                _stderr('! Error while processing media "{0}", {1}\n'.format(src, e))
                return False
        return True

    def build(self):
        """ Build this resource.
        """
        for size_name, sizes in self.config.media['image'].items():
            if not self.create_image(size_name, sizes):
                return False
            setattr(self, '%s_image_url' % size_name, partial(self.get_image_url, size_name=size_name))
        return True


class ResourceTree(dict):
    def __init__(self, nodes, **kwargs):
        dict.__init__(self, **kwargs)
        self.build(self, None, nodes)
        self[u'all'] = self.all()

    def build(self, tree, parent, nodes):
        if parent is not None:
            parent = parent.belongs_to
        children = [n for n in nodes if n.belongs_to_parent == parent]
        for child in children:
            if child.belongs_to not in tree:
                tree[child.belongs_to] = {u'list': []}
            if child not in tree[child.belongs_to][u'list']:
                tree[child.belongs_to][u'list'].append(child)
                # This key handling... must be able to simplify...
                tree[child.belongs_to][u'list'] = sorted(
                    tree[child.belongs_to][u'list'],
                    key=lambda r: r.destination,
                    reverse=True)
            self.build(tree[child.belongs_to], child, nodes)

    def all(self):
        a = self._all(self, [])
        return sorted(a, key=lambda r: r.destination, reverse=True)

    def _all(self, d, l):
        for k, v in d.iteritems():
            if k == 'list':
                for a in v:
                    l.append(a)
            if isinstance(v, dict):
                self._all(v, l)
        return l


class Pager(object):
    """
    Page the provided list of resources.
    """
    def __init__(self, page, all_resources, config):
        self.page = page
        self.config = config
        self.per_page = config.get('per_page', 20)
        self.total_pages = self.total_pages(all_resources, self.per_page)

        start_index = 0
        if self.total_pages > 0:
            start_index = (self.per_page * (self.page - 1))

        stop_index = self.page * self.per_page
        if self.page == self.total_pages:
            stop_index = len(all_resources)

        self.belongs_to, path_tail = os.path.split(all_resources[0].destination)
        self.belongs_to += '/' if not self.belongs_to.endswith('/') else ''

        self.total_resources = len(all_resources)
        self.resources = all_resources[start_index:stop_index]
        self.previous_page = self.page - 1 if self.page != 1 else None
        self.previous_page_path = self.path(self.previous_page)
        self.next_page = self.page + 1 if self.page != self.total_pages else None
        self.next_page_path = self.path(self.next_page)

    def __repr__(self):
        return '<Page %s of %s>' % (self.page, self.total_pages)

    def to_dict(self):
        return {
            'total_resources': self.total_resources,
            'total_pages': self.total_pages,
            'page': self.page,
            'resources': self.resources,
            'previous_page': self.previous_page,
            'previous_page_path': self.previous_page_path,
            'next_page': self.next_page,
            'next_page_path': self.next_page_path
        }

    def pageurl(self, page):
        path = self.config.get('url', 'page-{0}')
        return path.format(page)

    def path(self, page):
        if page is None or page < 1:
            return None
        if page == 1:
            return self.belongs_to
        return self.belongs_to + self.pageurl(page)

    @staticmethod
    def total_pages(all_resources, per_page):
        """
        Calculate total number of pages.
        """
        return int(math.ceil(float(len(all_resources)) / float(per_page)))


class Paginator(object):
    def __init__(self, site):
        self.site = site

    def paginate(self, config):
        name, c = config
        to_paginate = [r for r in self.site.resources if fnmatch.fnmatch(
            r.destination,
            c.get('pattern')
        )]
        self._paginate(to_paginate, config)

    def _paginate(self, resources, config):
        name, c = config
        per_page = c.get('per_page', 20)
        num_pages = Pager.total_pages(resources, per_page)
        for idx, r in enumerate(resources):
            #if r.destination.endswith('index.html'):
            if idx == 0:
                for page_num in range(1, num_pages + 1):
                    pager = Pager(page_num, resources, c)
                    if page_num > 1:
                        # Create new destination
                        r_copy = copy.deepcopy(r)
                        r_copy.pager = pager
                        path_head, path_tail = os.path.split(r_copy.source)
                        r_copy.source = path_head + u'/' + pager.pageurl(page_num) + u'/' + path_tail
                        self.site.resources.append(r_copy)
                    else:
                        r.pager = pager


class Site(object):
    """ Represent a Site to be built.
    """

    def __init__(self, config):
        self.config = config
        self.resources = []
        self.context = {}
        self.articles = []
        self.media = []

        if self.config.site_context:
            self.context.update(self.config.site_context)

        self.renderer = pystache.Renderer(
            search_dirs=[
                self.config.source_dir + os.sep + self.config.paths['layouts'],
            ],
            file_extension='html',
            file_encoding='utf-8',
            string_encoding='utf-8'
        )

    def _new_resource(self, path):
        """ Internal factory for creating a resource from path.
        """
        source_path = path.replace(self.config.source_dir, '', 1)
        if source_path.startswith(u'/_') or source_path.startswith(u'_'):
            return None
        if source_path.endswith('.md'):
            a = PageResource(self.config, source=source_path)
            if 'articles' not in self.context:
                self.context['articles'] = {}
            self.articles.append(a)
            return a
        elif path.endswith('.html'):
            r = PageResource(self.config, source=source_path)
            return r

    def read_directories(self):
        """ Scan directories for resources.
        """
        page_includes = [
            '*.html',
            '*.md',
            '*.txt',
        ]

        excludes = [
            os.path.basename(self.config.build_dir),
            self.config.paths['layouts'],
            self.config.paths['media']
        ]
        for root, dirs, files in os.walk(self.config.source_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in excludes]
            for pat in page_includes:
                for f in fnmatch.filter(files, pat):
                    r = self._new_resource(os.path.join(root, f))
                    if r:
                        # Add resources on the top, this forces childs to be rendered before their parents.
                        self.resources.insert(0, r)
        # TODO: Do these things in the loop above instead...
        for root, dirs, files in os.walk(
                os.path.join(self.config.source_dir,
                             self.config.paths['media']), topdown=True):
            files[:] = [f for f in files if not f.startswith(u'.')]
            for f in files:
                m = MediaResource(self.config, os.path.join(root, f))
                self.media.append(m)

        self.articles.sort(key=lambda r: len(r.destination))
        self.context['articles'] = ResourceTree(self.articles)

        paginator = Paginator(self)
        for c in self.config.pagination.items():
            paginator.paginate(c)

    def _build_media(self):
        failed = []
        for m in self.media:
            if not m.build():
                failed.append(m)
        # Remove all resources that we failed to build from media.
        self.media = list(set(self.media).difference(set(failed)))
        #self.media.sort(key=lambda r: len(r.destination))

        self.media = sorted(self.media, key=lambda r: r.destination, reverse=True)
        self.context[u'media'] = ResourceTree(self.media)

    def _build_static(self):
        """ Create directories needed for the structure.
        This step is done before most of the resources is moved to the build
        directory. It involves creation of directories for the structure and
        copying of assets.
        """
        modified_files = []
        for root, dirs, files in os.walk(
                os.path.join(self.config.source_dir,
                             self.config.paths['assets']), topdown=True):
            for d in dirs:
                src = os.path.join(root, d)
                dst = os.path.join(self.config.build_dir, self.config.paths['assets'], d)
                if not os.path.exists(dst):
                    mkdir_p(dst)
                    shutil.copystat(src, dst)
            # Ingore files starting with dot.
            files[:] = [f for f in files if not f.startswith('.')]
            for f in files:
                srcname = os.path.join(root, f)
                dstname = srcname.replace(self.config.source_dir, self.config.build_dir, 1)
                # Copy file if does not exists in build dir or if it has changed.
                if not os.path.exists(dstname) or os.path.exists(dstname) and os.stat(srcname).st_mtime != os.stat(dstname).st_mtime:
                    shutil.copy2(srcname, dstname)
                    modified_files.append(dstname)

        # Compare the asset directory with source to build and remove files
        # and directories that does not match.
        # Adapt this be a more generic comparison so we can diff all
        # resources.
        asset_dir = os.path.join(self.config.build_dir, self.config.paths['assets'])
        for root, dirs, files in os.walk(asset_dir, topdown=True):
            for d in dirs:
                compare = filecmp.dircmp(
                    os.path.join(self.config.source_dir, self.config.paths['assets'], d),
                    os.path.join(root, d)
                )
                for diff in compare.right_only:
                    p = os.path.join(asset_dir, d, diff)
                    if os.path.isdir(p):
                        try:
                            shutil.rmtree(p)
                        except OSError, e:
                            _stderr('** Could not remove directory {0} {1}\n'.format(p, e))
                    else:
                        try:
                            os.remove(p)
                        except OSError, e:
                            _stderr('** Could not remove file {0} {1}\n'.format(p, e))

        # If compression is enabled run it.
        if self.config.compress:
            import yuicompressor
            _stdout('** With compressing\n')
            for root, dirs, files in os.walk(self.config.build_dir + os.sep + self.config.paths['assets'], topdown=True):
                for pat in self.config.compress:
                    for f in fnmatch.filter(files, pat):
                        if not f.endswith('min.js') or not f.endswith('min.css'):
                            _stdout('>> {0}\n'.format(f))
                            yuicompressor.run(
                                os.path.join(root, f),
                                "-o", os.path.join(root, f)
                            )

    def build(self):
        """ Build this site and it resources.
        """
        _stdout('** Building site\n')
        # We start fresh on each build.
        self.context = {}
        self.resources = []
        self.articles = []
        self.media = []

        if not os.path.exists(self.config.build_dir):
            mkdir_p(self.config.build_dir)

        self.read_directories()
        self._build_media()
        self._build_static()

        _stdout('** Render resources\n')
        for r in self.resources:
            _stdout('>> {0}\n'.format(r.destination))
            r.render(self.renderer, self.context)

        _stdout('** Building resources\n')
        for r in self.resources:
            if r.should_build():
                _stdout('>> {0}\n'.format(r.destination))
                r.build()

    def find_resource(self, resource_id):
        """ Return an instance based on the id.
        """
        for r in self.resources:
            if r.id == resource_id:
                return r
        return None


class ResourceMonitor(threading.Thread):
    """ Monitor resources for changes.

    Example usage.

    >>> def onchange(paths):
    ...   print 'changed', paths
    ... 
    >>> ResourceMonitor(['.'], onchange).start()
    """
    def __init__(self, paths, onchange):
        threading.Thread.__init__(self)
        self.daemon = True
        self.paths = paths
        self.onchange = onchange
        self.modified_paths = {}

    def diff(self, path):
        """ Check for modifications returns a dict of paths and times of change.
        """
        modified_paths = {}
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                path = os.path.join(root, f)
                try:
                    modified = os.stat(path).st_mtime
                except Exception, e:
                    continue
                if path not in self.modified_paths or self.modified_paths[path] != modified:
                    modified_paths[path] = modified
        return modified_paths

    def _diffall(self):
        """ Run diff through all paths.
        """
        modified_paths = {}
        for p in self.paths:
            modified_paths.update(self.diff(p))
        return modified_paths

    def run(self):
        """ Starts monitoring, onchange is called if an resource is modified.
        """
        self.modified_paths = self._diffall()
        while True:
            modified_paths = self._diffall()
            if modified_paths:
                self.modified_paths.update(modified_paths)
                self.onchange(modified_paths)
            time.sleep(0.5)


def bootstrap():
    for p in Config.paths:
        mkdir_p(p)
        _stdout('+ ' + p + "\n")
    _stdout('"If you can see it, I can shoot it." - Cordero (Skeleton Man)' + "\n")


def build(config_path, **config):
    c = Config(config_path, **config)

    _stdout('Building to %s\n' % (c.build_dir))

    # TODO: Add a clean target...
    #try:
    #    shutil.rmtree(c.build_dir)
    #except OSError, e:
    #    pass

    site = Site(c)
    site.build()


def serve(config_path, port=8000, **config):
    c = Config(config_path, **config)

    c.source_dir = os.path.abspath(c.source_dir)
    c.build_dir = os.path.abspath(c.build_dir)

    site = Site(c)
    site.build()

    mkdir_p(c.build_dir)

    import SimpleHTTPServer
    import SocketServer

    class Server(SocketServer.ForkingMixIn, SocketServer.TCPServer):
        allow_reuse_address = True

    class RequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        pass

    try:
        server = Server(('', port), RequestHandler)
    except socket.error, e:
        _stderr('Could not start webserver. Are you running another one on the same port?')
        return

    def rebuild(modified_paths):
        _stdout('Rebuilding\n')
        for p in modified_paths:
            _stdout('Changed {0}\n'.format(p))
        # TODO: Pass the modified paths
        site.build()

    paths = [os.path.join(c.source_dir, p) for p in c.paths]

    monitor = ResourceMonitor(paths, rebuild)
    monitor.start()

    # Run server from our build directory.
    os.chdir(c.build_dir)

    _stdout('Running webserver at 0.0.0.0:%s for %s\n' % (port, c.build_dir))
    _stdout('Type control-c to exit\n')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    from optparse import OptionParser
    _cmd_parser = OptionParser(usage="usage: %prog [options]", version="%prog {0}".format(__version__))
    _opt = _cmd_parser.add_option
    _opt("-c", "--config", action="store", help="path to yaml configuration [default: %default].", default="config.yaml")
    _opt("-s", "--serve", action="store_true", help="start a webserver.")
    _opt("-p", "--port", action="store", help="set port for webserver [default: %default].", default=8000, dest="port")
    _opt("--bootstrap", action="store_true", help="create a new site here.")
    _opt("--build", action="store_true", help="build this site.")
    _opt("--debug", action="store_true", help="set debug mode.")
    _opt("--no-compress", action="store_true", help="do not compress css and js.", dest="no_compress", default=False)
    _cmd_options, _cmd_args = _cmd_parser.parse_args()

    opt, args, parser = _cmd_options, _cmd_args, _cmd_parser

    sys.path.insert(0, '.')
    sys.modules.setdefault('bakery', sys.modules['__main__'])

    if opt.bootstrap:
        bootstrap()
        sys.exit(0)
    elif opt.serve:
        try:
            port = int(opt.port)
        except ValueError, e:
            _stderr('Invalid value for port: {0}'.format(e))
            sys.exit(1)
        serve(opt.config, port, no_compress=opt.no_compress)
    elif opt.build:
        build(opt.config, no_compress=opt.no_compress)
        sys.exit(0)
    else:
        parser.print_help()
        _stderr('\nError: No options specified.\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
