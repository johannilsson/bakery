# Bakery

## A "Lightweight & Hackable" static site generator --- in other words yet another static site generator.

Bakery tries to makes it a little bit easier to create web sites while
applying a few tricks.

Bakery is built in Python based on the following components,
[Mustache](http://mustache.github.io/)
for templates,
[Markdown](http://daringfireball.net/projects/markdown/syntax) for text,
[Typogrify](https://github.com/mintchaos/typogrify) for typography,
[YUI Compressor](http://yui.github.io/yuicompressor/) for CSS and
JavaScript compression. [PIL](http://www.pythonware.com/products/pil/) for image manipulation. [YAML](http://www.yaml.org/) for configuration.

## Setup

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

A `config.yml` is needed for each site a minimal config looks like this.

    # Path to resources.
    source_dir: site
    # Path to where the site should be assembled
    build_dir: _out
    # Site context, this is passed to site and can be access through layouts.
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
	mkdir source
	vim config.yaml
	bakery --bootstrap
	bakery --serve

## Typography

The following is automatically applied.

* Three dots `...` into ...
* Single quotes `'` into curly quotes ' 
* Double quotes `"` into curly quotes "
* Two dashes `--` into --
* Three dashes `---` into ---

Widows is prevented using Widon't by applying a `&nbsp;` between the
two last words in common tags.

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

Articles are identified by their `.md` extension. A HTML page is
identified by it's `.html` extension. Articles are processed with
Markdown, HTML pages are not.

A page usually starts with a YAML frontmatter which is defined at the
top by three leading dashes and ends likewise. Any data defined here is
passed to the page when rendered.

Example page

    ---
    title: A Page
    layout: default.html
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


### Layouts

Layouts is usually used to wrap pages in various way. Pages can define
which layout it want to wrapped in by specifying a `layout` in the page
frontmatter, if no layout is specified `default.html` is assumed.

The most common is to define a layout that holds the common structure of
the site. A simple version of such a layout could look like this.

	<!doctype html>
	<html>
  	<link href="/assets/css/application.css" rel="stylesheet">
  	<title>{{page.title}}</title>
  	{{& page.content}}
	</html><

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

Media simplifies working with images.

This means automatic image scaling and categorization based on which directory
they're placed in.

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

Cheers!<br>
[Johan](http://johannilsson.com)
