# Bakery

## A "Lightweight & Hackable" static site generator

Bakery tries to make it a little bit easier to create web sites by applying a few tricks.

Bakery is built in Python based on the following components, [Mustache](http://mustache.github.io/)
for templates, [Markdown](http://daringfireball.net/projects/markdown/syntax) for text, [Typogrify](https://github.com/mintchaos/typogrify) for typography, [YUI Compressor](http://yui.github.io/yuicompressor/) for CSS and JavaScript compression. [PIL](http://www.pythonware.com/products/pil/) for image manipulation. [YAML](http://www.yaml.org/) for configuration.

## Typography

The following transformations is automatically applied.

* Three dots `...` into &#8230;
* Single quotes `'` into curly quotes &#8217;
* Double quotes `"` into curly quotes &#8221;
* Two dashes `--` into &#8212;
* Three dashes `---` into &#8211;

Widows is prevented using Widon't by applying a `&nbsp;` between the two last words in common tags.

All typography filters are provided through Typogrify which also adds
the following CSS hooks for additional styling.

* Single initial quote is wrapped with the class `quo`, double initial
  quotes are wrapped with the class `dquo`
* Ampersands are wrapped with the class `amp`.
* Multiple adjacent capital letters are wrapped with the class `caps`

## Building Blocks

Bakery consists of a set of blocks that is used to build a site. These
can be divided into pages, layouts, assets and media.

### Pages

A page can either be an Article or a HTML document.

Articles are identified by the `.md` extension. A HTML page is
identified by the `.html` extension. Articles are processed with
Markdown, HTML pages are not.

A page can start with a YAML frontmatter which is defined at the
top by three leading dashes and ends likewise. Any data defined here is
passed to the page when rendered.

Example page

    ---
    title: A Page
    mylist:
      - name: item1
      - name: item2
    ---
    # {{title}}

    We can render mylist from the yaml frontmatter like this.

    {{#mylist}}
      * {{name}}
    {{/mylist}}

Data defined in the frontmatter is also made available through layouts.
For instance, if you set a title, you can use it in your layout like
this:

	<title>{{page.title}}</title>

Articles is also added to the `{{site.articles}}` hash. This makes it
possible to list all articles like this.

    {{#site.articles.all}}
      * [{{title}}]({{url}})
    {{/site.articles.all}}

To list articles within a specific directory we would do this.

    {{#site.articles.another.list}}
      * [{{title}}]({{url}})
    {{/site.articles.another.list}}

#### Pagination

Page resources can be paginated based on a configuration. When a pattern match a set of resources the `pager` key will be injected into the root resource.

The following configuration will add pagination to of all posts that is placed in the directory posts.

    pagination:
      # The name of this pagination.
      posts:
        # Pattern to match, will collect all resources ending with .html in the
        # the posts directory and it sub-directories. Pattern matches against the
        # destination name and not the source name.
        pattern: /posts/*.html
        # Number of resources per page, default 20 if not specified.
        per_page: 10
        # Url for paging, must no match a resource name, '{0}' is where the page
        # number will be injected. Defaults to page-{0} if not specified.
        url: sida-{0}

We could also add pagination within the posts directory for better structure of the site. Name of the pagination - posts, dogs, cats in this example is not part of the matching rule. Pagination can be added to all parts of the site in a similar way. The following example will add pagination of all index files within the posts, dogs and cats directories.

    pagination:
      posts:
        pattern: /posts/*index.html
      dogs:
        pattern: /posts/dogs*index.html
      cats:
        pattern: /posts/cats*index.html

To paginate through our posts we would do this in our page located within the posts directory.

    {{#pager.resources}}
      * [{{title}}]({{url}})
    {{/pager.resources}}

	{{#pager}}
	Page {{pager.page}} of {{pager.total_pages}}
	{{/pager}}

	{{#pager.previous_page_path}}
	[Previous]({{pager.previous_page_path}})
	{{/pager.previous_page_path}}
	{{#pager.next_page_path}}
	[Next]({{pager.next_page_path}})
	{{/pager.next_page_path}}


Pager adds the following keys.

| key                      |
| ------------------------ |
| pager.total_resources    |
| pager.total_pages        |
| pager.page               |
| pager.resources          |
| pager.previous_page      |
| pager.previous_page_path |
| pager.next_page          |
| pager.next_page_path     |


### Layouts

Layouts can be used to wrap pages in various way. A Page can define which layout it want to wrapped with if no layout is specified, `default.html` is assumed.

To setup a Page with a alternative layout for a page we would use the layout keyword like this.

    ---
    title: A Page
    layout: mylayout.html
    mylist:
      - name: item1
      - name: item2
    ---
    # {{title}}

    We can render mylist from the yaml frontmatter like this.

    {{#mylist}}
      * {{name}}
    {{/mylist}}

A common usage of layouts is to define a layout that holds the common structure of the site. A simple version of such a layout could look like this.

	<!doctype html>
	<html>
  	<link href="/assets/css/application.css" rel="stylesheet">
  	<title>{{page.title}}</title>
  	{{& page.content}}
	</html>

The page content is rendered where the tag `{{& page.content}}` is. The
`&` is important here to tell Mustache to un-escape the content. The
`{{page.title}}` renderes the title which is defined in the page
frontmatter.

Within layouts one can also add partials which is fragments that can be
re-used accross the site. A fragment is rendered like this.

    {{> fragment}}

This will fetch the partial `fragment.html` from layouts which is normal HTML.

	<p>Hello from fragment.</p>


## Media

Adds automatic image scaling and categorization based on the directory the
image is placed in.

To enable scaling of images add the following to `config.yaml`.

    media:
      image:
        small:
          width: 200
          height: 200
        medium:
          width: 400
          height: 400
        large:
          width: 700
          height: 700

This configures three variants of the original image with the sizes
small, medium and large with different sizes. The naming of these is
dynamic so feel free to change them to s, m, l and add xl and xxl if
needed. The only mandatory here that a name to the size is applied.

Images goes into `media` and any sub directory within.

To show all images in the theo directory with the size medium:

	<ul>
	{{#site.media.theo.list}}
  		<li><img src="{{medium_image_url}}">
	{{/site.media.theo.list}}
	</ul>

As shown in the example the size of the image is accessed by referencing
the configured size name in the beginning. If we would have configured
the name of the `medium` size to `m` instead we would have accessed it with `{{m_image_url}}`.

## Installation & First steps

Install bakery with the following command.

	python setup.py install

Once installed the command line tool `bakery` is available with the following
commands.

	$ bakery
	Usage: bakery [options]

	Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -c CONFIG, --config=CONFIG
                            path to yaml configuration [default: config.yaml].
      -s, --serve           start a webserver.
      -p PORT, --port=PORT  set port for webserver [default: 8000].
      --bootstrap           create a new site here.
      --build               build this site.
      --debug               set debug mode.
      --no-compress         do not compress css and js.

A `config.yml` is needed for each site, a minimal config looks like this.

    # Path to resources.
    source_dir: site
    # Path to where the site should be assembled
    build_dir: _out
    # Site context, variables to be passed to site and can be access through layouts.
    site_context:
      media_url: 'http://example.com/media'
    # List of files to apply compression to. Basic regular expressions work
    # too, e.g. *.css and *.js. Files ending with min.js or min.css are
    # ingored. To not use compression, just remove compress or set it to
    # False.
    compress:
      - application.js
      - application.css

Steps needed to create a new site, to be simplified.

	mkdir example.com
	cd example.com
	mkdir site
	# Create a config.
	vim config.yaml
	bakery --bootstrap
	# Create a layout
	vim site/layouts/default.html
	# Create a root page.
	vim site/pages/index.html
	# Start the built in server
	bakery --serve

Cheers!<br>
[Johan](http://johannilsson.com)
