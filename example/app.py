import tornado.ioloop
import tornado.web
import sys
import logging
logging.basicConfig(level=logging.DEBUG)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    logging.info('Listening to - %s' % sys.argv[1])
    app = make_app()
    app.listen(sys.argv[1])
    tornado.ioloop.IOLoop.current().start()