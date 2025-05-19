####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

import json
from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.

    Add your own class fields and initialization code (e.g. to create forwarding table
    data structures). See the `Router` base class for docstrings of the methods to
    override.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        # TODO
        #  add your own class fields and initialization code here
        # routing table: dest -> (cost, port)
        self.routing_table = {addr : (0, None)}
        # neighbors: neighbor_addr -> (cost, port)
        self.neighbors = {}
        # luu cac vector gan nhat cua cac hang xom gui den
        self.neighbors_vector = {}

    def handle_packet(self, port, packet : Packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Gói dữ liệu thường
            if packet.dst_addr in self.routing_table:
                next_port = self.routing_table[packet.dst_addr][1]
                if next_port is not None:
                    self.send(next_port, packet)
        else:
            # Gói định tuyến DV
            neighbor_addr = packet.src_addr
            vector = json.loads(packet.content)
            # Chỉ cập nhật nếu vector thực sự thay đổi
            if self.neighbors_vector.get(neighbor_addr) != vector:
                self.neighbors_vector[neighbor_addr] = vector
                updated = self.recompute_route()
                if updated:
                    self.broadcast_distance_vector()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""
        self.neighbors[endpoint] = (cost, port)
        self.neighbors_vector.setdefault(endpoint, {})
        updated = self.recompute_route()
        if updated:
            self.broadcast_distance_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""
        remove_neighbor = None
        for neighbor, (nbr_cost, nbr_port) in self.neighbors.items():
            if nbr_port == port:
                remove_neighbor = neighbor
                break
        if remove_neighbor:
            del self.neighbors[remove_neighbor]
            self.neighbors_vector.pop(remove_neighbor, None)
        updated = self.recompute_route()
        if updated:
            self.broadcast_distance_vector()

    def handle_time(self, time_ms):
        """Handle current time."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_distance_vector()

    def recompute_route(self):
        # Bellman-Ford update
        new_table = {self.addr: (0, None)}
        # Đầu tiên, cập nhật cost trực tiếp đến hàng xóm
        for nbr, (cost, port) in self.neighbors.items():
            new_table[nbr] = (cost, port)
        # Bellman-Ford: kiểm tra qua từng hàng xóm
        for neighbor_addr, vector in self.neighbors_vector.items():
            if neighbor_addr not in self.neighbors:
                continue  # Bỏ qua nếu không còn là hàng xóm
            neighbor_cost, neighbor_port = self.neighbors[neighbor_addr]
            for dest, cost in vector.items():
                if dest == self.addr:
                    continue
                total = neighbor_cost + cost
                # Split horizon with poison reverse: không nhận lại route qua chính mình
                if dest in self.routing_table and self.routing_table[dest][1] == neighbor_port and cost >= 1e9:
                    continue
                if dest not in new_table or total < new_table[dest][0]:
                    new_table[dest] = (total, neighbor_port)
        # Nếu có thay đổi thì cập nhật
        if new_table != self.routing_table:
            self.routing_table = new_table
            return True
        return False

    def broadcast_distance_vector(self):
        # Split horizon with poison reverse: gửi cost vô cực cho hàng xóm nếu next hop là chính nó
        for port in self.links.keys():
            vector = {}
            for dest, (cost, out_port) in self.routing_table.items():
                # Nếu next hop đi qua port này thì gửi poison reverse
                if out_port == port and dest != self.addr:
                    vector[dest] = 1e9  # Giá trị lớn đại diện cho vô cực
                else:
                    vector[dest] = cost
            packet = Packet(
                kind=Packet.ROUTING,
                src_addr=self.addr,
                dst_addr=None,
                content=json.dumps(vector)
            )
            self.send(port, packet)

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        # TODO
        #   NOTE This method is for your own convenience and will not be graded
        return f"DVrouter(addr={self.addr}, table={self.routing_table}, neighbors={self.neighbors})"