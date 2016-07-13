#!/usr/bin/python3
import asyncio
import signal
import random

class Color(object):
    def __init__(self, color_name, min_max):
        self.color_name = color_name
        self.min_max = min_max
        self.next = None
    
    def next_color(self):
        return self.next
    
    def __repr__(self, *args, **kwargs):
        return "<Color %s>" % self.color_name

red = Color("red", (5,10))
green = Color("green", (10,15))
yellow = Color("yellow", (2,4))
red.next = green
green.next = yellow
yellow.next = red

class SemaphoreProtocol(asyncio.Protocol):
    def __init__(self, factory):
        self.factory = factory
        self.factory.add_protocol(self) # outro meio de fazer isso?

    def connection_made(self, transport):
        self.transport = transport
        # isso eh necessario? Nao tem outro meio de faze-lo?
        self.send_color()
    
    def send_color(self, color=None):
        if not color:
            color = self.factory.get_current_color()
        self.write_line(color)

    def write_line(self, data):
        data += "\n"
        self.transport.write(data.encode())

    def data_received(self, data):
        data = data.decode().strip("\n").strip('\r')
        if data in ['green', 'red', 'yellow']:
            set_color = self.factory.set_color(data)
            self.write_line(str(set_color))
        elif data:
            self.send_color()

    def connection_lost(self, exc):
        self.factory.remove_protocol(self)


class Factory(object):
    def __init__(self, loop):
        self.loop = loop
        self.current_color = red
        self.protocols = []
        self.call_later = None
        self.change_color()
        
    
    def add_protocol(self, protocol):
        self.protocols.append(protocol)
    
    def remove_protocol(self, protocol):
        self.protocols.remove(protocol)
    
    def set_color(self, new_color):
        next_color_name = self.current_color.next_color().color_name
        if new_color == next_color_name:
            print("changing color as requested")
            self.call_later.cancel()
            self.change_color()
            return True
        else:
            print("not this time babe, I could only change the color to %s" %(next_color_name))
            return False
    
    def change_color(self):
        self.current_color = self.current_color.next_color()
        self.color_changed()
    
    def color_changed(self):
        time_to_wait = random.randint(*self.current_color.min_max)
        print("waiting %ss to change color from %s to %s \n" % (time_to_wait,
                                                            self.current_color.color_name,
                                                            self.current_color.next_color().color_name))
        self.call_later = self.loop.call_later(time_to_wait, self.change_color)
        new_color = self.get_current_color()
        for protocol in self.protocols:
            protocol.send_color(new_color)
    
    def get_current_color(self):
        return self.current_color.color_name
    
        
def start_server(loop, host, port):
    factory = Factory(loop)
    ugliest_thing = lambda: SemaphoreProtocol(factory) # ?????????
    f = loop.create_server(ugliest_thing, host, port)
    return loop.run_until_complete(f)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    server = start_server(loop, "0.0.0.0", 9999)

    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()