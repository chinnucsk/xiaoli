#!/usr/bin/env python
# coding: utf-8
from datetime import datetime

from flask import Blueprint, request, session, url_for,\
    redirect, render_template, g, flash
from flask import json, send_file

from sqlalchemy import or_

from tango import db,get_profile
from tango.ui.tables import make_table
from tango.login import current_user
from tango.models import Profile, Category
from tango.excel import XlsExport

from .models import NodeEoc,NODE_STATUS_DICT, Area, Node,Vendor
from .tables import EocTable
from .forms import  EocSearchForm, EocNewForm
from .views import nodeview

@nodeview.route('/nodes/eocs.xls/', methods=['POST', 'GET'])
@nodeview.route('/nodes/eocs/', methods=['POST', 'GET'])
def eocs():
    form = EocSearchForm()
    query = NodeEoc.query.outerjoin(Area, NodeEoc.area_id==Area.id)

    query_dict = dict([(key, request.args.get(key))for key in form.data.keys()])
    if query_dict.get("keyword"):
        query=query.filter(or_(
            NodeEoc.name.like('%'+query_dict["keyword"]+'%'),
            NodeEoc.alias.like('%'+query_dict["keyword"]+'%'),
            NodeEoc.addr.like('%'+query_dict["keyword"]+'%')
        ))
    if query_dict.get("area"):
        netloc = request.args.get('area_netloc')
        print netloc
        if 'or' in netloc: netloc = '('+netloc+')'
        query = query.filter(netloc)
    if query_dict.get("vendor_id"): query=query.filter(NodeEoc.vendor_id == query_dict["vendor_id"]) # ==
    if query_dict.get("model_id"): query=query.filter(NodeEoc.model_id == query_dict["model_id"])    # ==
    if query_dict.get("status"): query=query.filter(NodeEoc.status == query_dict["status"])
    if not current_user.is_province_user: query = query.filter(current_user.domain.clause_permit)
    form.process(**query_dict)
    table = make_table(query, EocTable)

    status_statistcs = []
    for status in NODE_STATUS_DICT.keys():
        num = NodeEoc.query.filter(NodeEoc.status == status)
        if not current_user.is_province_user: num = num.outerjoin(Area, NodeEoc.area_id==Area.id).filter(current_user.domain.clause_permit)
        num = num.count()
        status_statistcs.append({"status": status, "number": num, "name": NODE_STATUS_DICT.get(status)})

    if request.base_url.endswith(".xls/"):
        csv = XlsExport('eocs',columns=NodeEoc.export_columns())
        return send_file(csv.export(query,format={'status': lambda value: NODE_STATUS_DICT.get(value)}),as_attachment=True,attachment_filename='eocs.xls')
    else:
        return render_template('/nodes/eocs/index.html', table = table, form=form, status_statistcs=status_statistcs)

@nodeview.route('/nodes/eocs/new/', methods=['GET','POST'])
def eocs_new():
    next = request.form["next"] if request.form.get("next") else request.referrer
    form = EocNewForm()
    if request.method == 'POST' and form.validate_on_submit():
        del form._fields["cityid"]
        del form._fields["town"]
        node = NodeEoc()
        form.populate_obj(node)
        if NodeEoc.query.filter(NodeEoc.name==node.name).count() > 0:
            flash(u'EOC名称不能重复','error')
        elif NodeEoc.query.filter(NodeEoc.alias==node.alias).count() > 0:
            flash(u'EOC别名不能重复','error')
        elif Node.query.filter(Node.addr==node.addr).count() > 0:
            flash(u'IP地址不能重复','error')
        else:
            node.status = 1
            node.category_id = 50
            db.session.add(node)
            db.session.commit()
            flash(u'添加EOC %s 成功'% node.name, 'success')
            return redirect(url_for('nodes.eocs'))
    return render_template('nodes/eocs/new.html', form = form, next=next)

@nodeview.route('/nodes/eocs/edit/<int:id>/', methods=['POST', 'GET'])
def eocs_edit(id):
    next = request.form["next"] if request.form.get("next") else request.referrer
    form = EocNewForm()
    node = NodeEoc.query.get_or_404(id)
    if request.method == 'POST':
        if form.validate_on_submit():
            if node.name != form.name.data and NodeEoc.query.filter(NodeEoc.name==form.name.data).count() > 0:
                flash(u'EOC名称不能重复','error')
            elif node.alias != form.alias.data and NodeEoc.query.filter(NodeEoc.alias==form.alias.data).count() > 0:
                flash(u'EOC别名不能重复','error')
            elif node.addr != form.addr.data and Node.query.filter(Node.addr==form.addr.data).count() > 0:
                flash(u'IP地址不能重复','error')
            else:
                del form._fields["cityid"]
                del form._fields["town"]
                form.populate_obj(node)
                node.updated_at = datetime.now()
                db.session.add(node)
                db.session.commit()
                flash(u'修改EOC %s 成功'% node.name,'success')
                return redirect(url_for('nodes.eocs'))
    else:
        form.process(obj=node)
    return render_template('/nodes/eocs/edit.html', node=node, form=form, next=next)

@nodeview.route('/nodes/eocs/delete/', methods=['POST'])
def eocs_delete():
    if request.method == 'POST':
        ids = request.form.getlist('id')
        for id in ids:
            node = NodeEoc.query.get(id)
            db.session.delete(node)
        db.session.commit()
        flash(u'删除EOC成功','success')
        return redirect(url_for('nodes.eocs'))

@nodeview.route('/nodes/eocs/<int:id>/', methods=['GET'])
def eocs_show(id):
    node = NodeEoc.query.get(id)
    if node is None:
        return render_template('/nodes/not_exist.html', menuid='eocs', message=u'EOC不存在，可能已经被删除',title=u'EOC')
    chartdata = [
            {
            "area": True,
            "key" : u"接收流量" ,
            "color": 'lime',
            "values" : [ {'x':1352937600000 , 'y':27.38478809681} ,
                    { 'x':1352947600000 , 'y':27.371377218208} ,
                    { 'x':1352957600000 , 'y':26.309915460827} ,
                    {  'x':1352967600000 , 'y':26.425199957521} ,
                    {  'x':1352977600000 ,'y': 26.823411519395} ,
                    {  'x':1352987600000 ,'y': 23.850443591584} ,
                    {  'x':1352997600000 ,'y': 23.158355444054} ,
                    {  'x':1353007600000 , 'y':22.998689393694} ,
                    {  'x':1353017600000 ,'y': 27.977128511299} ,]
        } ,
            {
            "area": True,
            "color": '#773EF7',
            "key" : u"发送流量" ,
            "values" :[{'x':1352937600000 , 'y':12} ,
                    { 'x':1352947600000 , 'y':110} ,
                    { 'x':1352957600000 , 'y':110} ,
                    {  'x':1352967600000 , 'y':30} ,
                    {  'x':1352977600000 ,'y': 60} ,
                    {  'x':1352987600000 ,'y': 6} ,
                    {  'x':1352997600000 ,'y': 12} ,
                    {  'x':1353007600000 , 'y':10} ,
                    {  'x':1353017600000 ,'y': 0} ,]
        } ,
    ];
    data = [{'label': u'完全故障', 'color': 'red', 'value': 1},
            {'label': u'部分故障', 'color': 'yellow', 'value': 2},
            {'label': u'完全正常', 'color': 'green', 'value': 19},
            {'label': u'数据缺失', 'color': 'blue', 'value': 2}]
    chartdata2 = [{'values': data}]
    return render_template('nodes/eocs/show.html', node = node, chartdata = chartdata, chartdata2 = chartdata2)

import os
import operator
from flask import Markup
from werkzeug import secure_filename
@nodeview.route('/nodes/eocs/import/', methods=['POST'])
def eocs_import():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('xls'):
            filename = secure_filename(file.filename)
            root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','static','file','upload')
            if not os.path.isdir(root_path): os.mkdir(root_path)
            file_path = os.path.join(root_path, filename.split('.')[0]+datetime.now().strftime('(%Y-%m-%d %H-%M-%S %f)')+'.xls')
            file.save(file_path)
            from tango.excel import EocImport
            reader = EocImport(engine=db.session.bind)
            vendor_dict = dict([(vendor.alias, vendor.id) for vendor in Vendor.query.filter(Vendor.is_valid==1).all()])
            info = reader.read(file=file_path, data_dict={'branch_name':current_user.domain.import_permit(3),'vendor_id':vendor_dict,'snmp_ver':['v1','v2c']})
            flash(Markup(info), 'success')
        else:
            flash(u"上传文件格式错误", 'error')
    return redirect(url_for('nodes.eocs'))
