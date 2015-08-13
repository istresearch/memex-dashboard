import traceback

class WsgiLogErrors(object):
    def process_exception(self, request, exception):
        tb_text = traceback.format_exc()
        url = request.build_absolute_uri()
        request.META['wsgi.errors'].write(url + '\n' + str(tb_text) + '\n')
