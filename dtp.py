import sys
import re
import json
from datetime import datetime
from Node import Node

"""
Dream Team Parser
@Version: DEV
@Copy Right: University of California, Berkeley - ACE Lab

Parser for Dream Team GUI - a Concept Map
"""
class DreamTeamParser:
    PRE_INFO_PATTERN = r'[\s]*/\*[\s]*Priority\sLevel\s=\s([1-5])[\s]*' \
                       r'Time\s=\s([\d]{2})([\d]{2})([\d]{4})[\s]*\*/[\s]*'
    NODE_PATTERN = r'[\s]*node([\d]+)\[label = "([A-Za-z\d\s]+)"'
    PATH_PATTERN = r'[\s]*node([\d]+)[\s]*->[\s]*node([\d]+);[\s]*\n'
    MULTI_PATH_MATCH_PATTERN = re.compile(r'[\s]*\{(node(\d)+,\s)+node(\d)+\}[\s]*->[\s]*node([\d]+);[\s]*\n')
    MULTI_PATH_EXTRACT_PATTERN = re.compile(r'node(\d+)')

    def __init__(self, file_name, priority_cutoff):
        self.file_name = file_name
        self.dot = open("{}.dot".format(file_name), "r")
        self.dtm = open("{}_DTM.json".format(file_name), "r")
        self.priority_cutoff = priority_cutoff
        self.dot_lines = self.dot.readlines()
        self.nodes = []
        self.filtered_nodes = []
        self.paths = []
        self.filtered_paths = []
        self.classes = {}
        self.rankdir = ""
        self.log = ""
        self.log += "{}: DreamTeamParser initialized with dot file target {}.dot and " \
                    "priority level {}\n".format(datetime.now(), self.file_name, self.priority_cutoff)

    def read_json(self):
        dtm_data = json.load(self.dtm)
        self.rankdir = dtm_data["rankdir"]
        self.classes = dtm_data["styles"]
        for node in dtm_data["nodes"]:
            self.add_node(node["name"], node["label"], node["priority"], node["week"], node["class"])
        for path in dtm_data["edges"]:
            start = path["from"]
            for end in path["to"]:
                self.paths.append((start, end))
        self.post_filter_all_paths()
        return

    def read_dot(self):
        for i in range(len(self.dot_lines)):
            dot_line = self.dot_lines[i]
            if re.compile(DreamTeamParser.PRE_INFO_PATTERN).fullmatch(dot_line):
                dot_line_ahead = self.dot_lines[i + 1]
                self.read_node(dot_line, dot_line_ahead)
            elif re.compile(DreamTeamParser.PATH_PATTERN).fullmatch(dot_line):
                self.read_path(dot_line)
            elif re.compile(DreamTeamParser.MULTI_PATH_MATCH_PATTERN).fullmatch(dot_line):
                self.read_multi_path(dot_line)
        self.log += "{}: Parsing completed \n".format(datetime.now())
        self.log += "{}: Parsed {} nodes \n".format(
            datetime.now(), len(self.nodes))
        self.log += "{}: Parsed {} paths \n".format(
            datetime.now(), len(self.paths))
        self.log += "{}: Begin verify paths \n".format(datetime.now())
        self.post_filter_all_paths()
        self.log += "{}: Parsed and verified {} paths \n".format(
            datetime.now(), len(self.paths))

    def read_node(self, dot_line, dot_line_ahead):
        if not re.compile(DreamTeamParser.NODE_PATTERN).match(dot_line_ahead):
            self.log += "{}: Invalid definition ({}) after pre info ({})\n".format(
                datetime.now(), dot_line, dot_line_ahead)
        pre_info = re.search(DreamTeamParser.PRE_INFO_PATTERN, dot_line).groups()
        priority, month, day, year = map(lambda x: int(x), pre_info)
        node = re.search(DreamTeamParser.NODE_PATTERN, dot_line_ahead).groups()
        name, text = int(node[0]), node[1]
        if priority <= self.priority_cutoff:
            self.add_node(name, text, priority, month, day, year)
        else:
            self.log += "{}: Node{} with priority level {} ignored under cutoff {}\n".format(
                datetime.now(), name, priority, self.priority_cutoff)

    def expand_node(self, name):
        if name < len(self.nodes):
            return
        else:
            difference = name - len(self.nodes) + 1
            self.nodes += [None] * difference
            self.filtered_nodes += [None] * difference

    def add_node(self, name, text, priority, week, style_class):
        self.expand_node(name)
        new_node = Node(name, text, priority, week, style_class)
        if priority <= self.priority_cutoff:
            self.filtered_nodes[name] = new_node
        else:
            self.log += "{}: Node{} with priority level {} ignored under cutoff {}\n".format(
                datetime.now(), name, priority, self.priority_cutoff)
        self.nodes[name] = new_node
        return

    def read_path(self, dot_line):
        path_info = re.search(DreamTeamParser.PATH_PATTERN, dot_line).groups()
        self.paths.append((int(path_info[0]), int(path_info[1])))

    def read_multi_path(self, dot_line):
        path_info = re.findall(DreamTeamParser.MULTI_PATH_EXTRACT_PATTERN, dot_line)
        for i in range(len(path_info)-1):
            self.paths.append((int(path_info[i]), int(path_info[-1])))

    def post_filter_all_paths(self):
        filtered_paths = []
        for i in range(len(self.paths)):
            start, end = self.paths[i]
            if start >= len(self.nodes) or end >= len(self.nodes):
                self.log += "{}: Path {} to {} refers to undefined node(s) \n".format(
                    datetime.now(), start, end)
            else:
                if self.filtered_nodes[start] is not None and self.filtered_nodes[end] is not None:
                    filtered_paths.append((self.nodes[start], self.nodes[end]))
                    self.nodes[start].add_child(self.nodes[end])
                    self.nodes[end].add_parent(self.nodes[start])
                else:
                    self.log += "{}: Path {} to {} refers to undefined node(s) \n".format(
                        datetime.now(), start, end)
        self.filtered_paths = filtered_paths

    def to_json(self):
        nodes_json = []
        for node in self.filtered_nodes:
            if node is not None:
                node_json = {'name': str(node.get_name()),
                             'label': node.get_text(),
                             'week': node.get_week()}
                nodes_json.append(node_json)
        paths_json = []
        for path in self.filtered_paths:
            path_json = {'start': str(path[0].get_name()),
                         'end': str(path[1].get_name())}
            paths_json.append(path_json)
        all_data_json = {'nodes': nodes_json, 'paths': paths_json}
        with open('{}.json'.format(self.file_name), 'w', encoding='utf-8') as json_file:
            json.dump(all_data_json, json_file, indent=4)
        self.log += "{}: Wrote to JSON; File titled {}.json\n".format(
            datetime.now(), self.file_name)

    def write_dot(self):
        dot = "digraph G {\n"
        dot += "\trankdir = {}\n".format(self.rankdir)
        for node in self.nodes:
            if node is not None:
                style_class = self.classes[node.get_style_class()]
                shape, style, fillcolor = style_class["shape"], style_class["style"], style_class["fillcolor"]
                dot += '''\tnode{}[label = "{}", shape = {}, style = {}, fillcolor = "{}"];\n'''.format(node.get_name(),
                                                                                                        node.get_text(),
                                                                                                        shape,
                                                                                                        style,
                                                                                                        fillcolor)
        for path in self.paths:
            dot += "\tnode{} -> node{};\n".format(path[0], path[1])
        dot += "}\n"
        with open('{}_DTP_DOT.dot'.format(self.file_name), 'w', encoding='utf-8') as dot_file:
            dot_file.write(dot)

    def write_log(self):
        with open('{}_DTP_log.txt'.format(self.file_name), 'w', encoding='utf-8') as log_file:
            log_file.write(self.log)
        print(self.log)
        print("{}: Wrote to log file; "
              "File titled {}_parser_log.txt".format(datetime.now(), self.file_name))

    def close_files(self):
        self.dtm.close()

    def parse(self):
        self.read_json()
        self.to_json()
        self.write_dot()
        self.write_log()
        self.close_files()


if __name__ == '__main__':
    DTP = DreamTeamParser(file_name=sys.argv[1], priority_cutoff=int(sys.argv[2]))
    DTP.parse()
