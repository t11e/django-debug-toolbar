"""
Debug Toolbar middleware
"""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.utils.encoding import smart_unicode
from django.conf.urls.defaults import include, patterns
import debug_toolbar.urls
from debug_toolbar.toolbar.loader import DebugToolbar

_HTML_TYPES = ('text/html', 'application/xhtml+xml')

def replace_insensitive(string, target, replacement):
    """
    Similar to string.replace() but is case insensitive
    Code borrowed from: http://forums.devshed.com/python-programming-11/case-insensitive-string-replace-490921.html
    """
    no_case = string.lower()
    index = no_case.find(target.lower())
    if index >= 0:
        return string[:index] + replacement + string[index + len(target):]
    else: # no results so return the original string
        return string

class DebugToolbarMiddleware(object):
    """
    Middleware to set up Debug Toolbar on incoming request and render toolbar
    on outgoing response.
    """
    def __init__(self):
        self.debug_toolbar = None
        self.original_urlconf = settings.ROOT_URLCONF
        self.original_pattern = patterns('', ('', include(self.original_urlconf)),)
        self.override_url = True

    def show_toolbar(self, request):
        if not settings.DEBUG:
            return False
        if request.is_ajax():
            return False
        if settings.INTERNAL_IPS and request.META.get('REMOTE_ADDR') not in settings.INTERNAL_IPS:
            return False
        return True

    def process_request(self, request):
        if self.override_url:
            debug_toolbar.urls.urlpatterns += self.original_pattern
            self.override_url = False
        request.urlconf = 'debug_toolbar.urls'

        if self.show_toolbar(request):
            self.debug_toolbar = DebugToolbar(request)
            for panel in self.debug_toolbar.panels:
                panel.process_request(request)

        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.debug_toolbar:
            for panel in self.debug_toolbar.panels:
                panel.process_view(request, view_func, view_args, view_kwargs)

    def process_response(self, request, response):
        if not self.debug_toolbar:
            return response
        if self.debug_toolbar.config.intercept_redirects:
            if isinstance(response, HttpResponseRedirect):
                redirect_to = response.get('Location', None)
                if redirect_to:
                    response = render_to_response(
                        'debug_toolbar/redirect.html',
                        {'redirect_to': redirect_to}
                    )
        if response.status_code != 200:
            return response
        for panel in self.debug_toolbar.panels:
            panel.process_response(request, response)
        if response['Content-Type'].split(';')[0] in _HTML_TYPES:
            if self.debug_toolbar.config.logging_enabled:
                uid = self.debug_toolbar.serialize()
                response.set_cookie('debug_toolbar_detail_url', value='http://%s:%s/__debug__/logs/%s/' % (request.META['SERVER_NAME'], uid))
            if self.debug_toolbar.config.toolbar_enabled:
                response.content = replace_insensitive(smart_unicode(response.content), u'</body>', smart_unicode(self.debug_toolbar.render_toolbar() + u'</body>'))
        return response
