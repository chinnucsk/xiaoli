#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, request, session, url_for, \
    redirect, render_template, g, flash

import pydot
from tango.ui import menus, Menu
from nodes.models import Node, Area

topoview = Blueprint('topo', __name__)

area_style = {
    'shape' : 'polygon',
    # 'sides' : 4,
    'style' : 'filled',
    'color' : 'lightblue',
    # 'peripheries': 2,
    'fontsize' : '12.0'
}

node_style = {
    'shape' : 'ellipse',
    'style' : 'filled',
    'color' : '#999999',
    'fillcolor' : 'orange',
    'fontsize' : '10.0'
}

area_edge_style = {
    'color' : 'skyblue',
    'labelfontcolor' : '#009933',
}

node_edge_style = {
    'labelfontcolor' : '#009933',
}

@topoview.route('/topo/')
def index():
    node_url = lambda id : url_for('nodes.node_edit', id=id)

    graph = pydot.Dot(graph_type='digraph')
    def mk_areas(root):
        if root is None:
            return

        area_root = pydot.Node('areas_%d' % root.id, label=root.name, **area_style)
        graph.add_node(area_root)

        node_nodes = Node.query.filter_by(area_id=root.id)
        for node in node_nodes:
            n_current = pydot.Node('nodes_%d' % node.id, label='%s\n%s' % (node.name, node.addr),
                                   URL=node_url(node.id))
            graph.add_node(n_current)
            graph.add_edge(pydot.Edge(area_root, n_current))

            if node.controller_id:
                controller = Node.query.get(node.controller_id)
                node_id = 'nodes_%d' % node.controller_id
                n_controller =  graph.get_node(node_id)
                if not n_controller:
                    n_controller = pydot.Node('nodes_%d' % controller.id, label='%s\n%s' % (node.name, node.addr))
                    graph.add_node(n_controller)
                else:
                    n_controller = n_controller[0]
                graph.add_edge(pydot.Edge(n_controller, n_current))

        for child in root.children:
            node_child = mk_areas(child)
            graph.add_node(node_child)
            graph.add_edge(pydot.Edge(area_root, node_child, **area_edge_style))

        return area_root

    graph.set_node_defaults(**node_style)
    graph.set_edge_defaults(**node_edge_style)

    root_area = Area.query.get(1000)
    mk_areas(root_area)
    svg = unicode(graph.create(prog='dot', format='svg'), 'utf-8')
    svg = svg[245:]
        
    return render_template("topo/index.html", svg=svg, menuid = 'topo')


@topoview.route('/viewtopo/')
def viewtopo():
    root_id = request.args.get('root_id', 1000, type=int)
    level = request.args.get('level', 3, type=int)
    prog = request.args.get('prog', 'dot')
    area_url = lambda root_id : url_for('topo.viewtopo', root_id=root_id,
                                        level=level, prog=prog)
    node_url = lambda node_id : url_for('nodes.node_edit', id=node_id)
    
    graph = pydot.Dot(graph_type='digraph')
    root_area = Area.query.get_or_404(root_id)

    def add_node(node):
        node_id = 'nodes_%d' % node.id
        node_node =  graph.get_node(node_id)
        if not node_node:
            node_node = pydot.Node(node_id, label='%s\n%s' % (node.name, node.addr),
                                         URL=node_url(node.id), **node_style)
            graph.add_node(node_node)
        else:
            node_node = node_node[0]
        return node_node
        
    def touch_nodes(root, level=level):
        if level == 0:
            return
        area_children = root.children
        node_children = Node.query.filter(Node.area_id==root.id).all()
        cur_area_attrs = area_style.copy()
        cur_area_attrs['peripheries'] = 2 if area_children else 1
        cur_area_attrs['fillcolor'] = 'lightgreen' if node_children else 'lightblue'
        if node_children or area_children:
            cur_area_attrs['URL'] = area_url(root.id)
        else:
            cur_area_attrs['color'] = 'silver'
            cur_area_attrs['fillcolor'] = 'lightgray'
            
        root_node =  pydot.Node('areas_%d' % root.id, label=root.name, **cur_area_attrs)
        graph.add_node(root_node)

        # touch areas
        for child_area in area_children:
            child_area_node = touch_nodes(child_area, level=level-1)
            if child_area_node:
                graph.add_edge(pydot.Edge(root_node, child_area_node, **area_edge_style))

        if level == 1:
            return root_node
        # touch nodes
        for node in node_children:
            node_node = add_node(node)
            graph.add_edge(pydot.Edge(root_node, node_node, color='orange', **node_edge_style))
            # touch controller node
            if node.controller_id:
                controller = Node.query.get(node.controller_id)
                controller_node = add_node(controller)
                graph.add_edge(pydot.Edge(controller_node, node_node, color='orchid', **node_edge_style))
        return root_node

    touch_nodes(root_area)
    base = root_area
    breadcrumb = [base]
    while base.parent:
        breadcrumb.append(base.parent)
        base = base.parent
    svg = unicode(graph.create(prog=prog, format='svg'), 'utf-8')
    svg = svg[245:]
    return render_template("topo/index.html", svg=svg, breadcrumb=breadcrumb)
    
    
menus.append(Menu('topo', u'拓扑', '/topo'))
