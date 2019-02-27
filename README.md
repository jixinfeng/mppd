# mppd
A minimalistic python podcast downloader

Aimed to download old NPR Planet Money podcasts provided by [this repo](https://github.com/xjcl/planetmoney-rss),
will test on other feeds in the future

Requires feedparser

Audiobook build scripts requires [Audiobook Binder](http://bluezbox.com/audiobookbinder.html), make sure the `abbinder` is in your `$PATH`

# Known Issue

`abbinder` may throw segfault at chapter building phase at the end of file conversion, especially when chapter list is long
