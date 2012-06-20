# -*- coding: utf-8 -*-
from string import Template
import datetime
import math
import os.path
import string

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.utils.translation import ugettext_lazy as _, ungettext

from flooding_lib.dates import get_intervalstring_from_dayfloat
from flooding_lib.forms import AttachmentForm
from flooding_lib.forms import EditScenarioPropertiesForm
from flooding_lib.forms import ScenarioNameRemarksForm
from flooding_lib.forms import TaskApprovalForm
from flooding_lib.models import Attachment
from flooding_lib.models import ExternalWater
from flooding_lib.models import ExtraInfoField
from flooding_lib.models import ExtraScenarioInfo
from flooding_lib.models import Scenario
from flooding_lib.models import ScenarioBreach
from flooding_lib.models import SobekModel
from flooding_lib.models import Task
from flooding_lib.models import TaskType
from flooding_lib.models import UserPermission
from flooding_lib.permission_manager import PermissionManager
from flooding_lib.tools.approvaltool.views import approvaltable
from flooding_lib.tools.importtool.models import InputField
from flooding_presentation.models import Animation


def format_timedelta(t_delta):
    """
    - Formats the timedelta to "x days, y hours"
    """
    nrdays = t_delta.days
    nrhours = math.floor(t_delta.seconds / 3600)
    str_days = (ungettext('%(nrdays)d day', '%(nrdays)d days', nrdays)
                % {'nrdays': nrdays})
    str_hours = (ungettext('%(nrhours)d hour', '%(nrhours)d hours', nrhours)
                 % {'nrhours': nrhours})
    return str_days + ", " + str_hours


def infowindow(request):
    # action and scenarioid can be in get or post (to keep the
    # javascript RPC-calls simple) therefore we use REQUEST instead of
    # GET or POST
    action_name = request.REQUEST.get('action')
    scenario_id = request.REQUEST.get('scenarioid')

    scenario = get_object_or_404(Scenario, pk=scenario_id)

    if action_name == 'information':  # GET
        return infowindow_information(scenario)

    elif action_name == 'remarks':  # POST AND GET difference handled
                                    # in 'return method'
        callbackfunction = request.REQUEST.get('callback')
        form_id = request.REQUEST.get('formId')
        return infowindow_remarks(
            request, scenario_id, callbackfunction, form_id)

    elif action_name == 'approval':  # POST AND GET difference handled
                                     # in 'return method'
        callbackfunction = request.REQUEST.get('callback')
        callbackfunction.replace("%22", '"')
        form_id = request.REQUEST.get('formId')
        with_approvalobject = request.REQUEST.get('with_approvalobject', 1)
        if int(with_approvalobject) == 0:
            with_approvalobject = False
        else:
            with_approvalobject = True

        return infowindow_approval(
            request, scenario_id, callbackfunction,
            form_id, with_approvalobject)

    elif action_name == 'edit':
        return infowindow_edit(request, scenario_id)

    elif action_name == 'editproperties':
        return editproperties(request, scenario_id)

    elif action_name == 'showattachments':
        return showattachments(request, scenario_id)


def scenario_information(scenario):
    fields = [
        # Scenario identificatie
        (_('Scenario name'), scenario.name),
        # Scenario datum
        (_('Project name'), scenario.project.friendlyname),
        # Eigenaar overstromingsinformatie
        # Beschrijving scenario
        # Versie resultaat
        # Motivatie rekenmethode
        # Doel
        # Berekeningsmethode
        # Houdbaarheid scenario
        ]

    return fields + scenario.get_scenario_overview_extra_info(
        ExtraInfoField.HEADER_SCENARIO)


def infowindow_information(scenario):
    """
    - Get the list of headers and fields that the importtool has
    - If the importtool field says that the data is stored in a
      ExtraInfoField, use that to show the data
    - Otherwise, if it's a known field on a known object, getattr it
      from that
    - Only keep fields with a value, only keep headers with fields

    We need to add some fields that the importtool doesn't have;
    scenario.id and attachments come to mind. So we're going to
    manually add some fields to the start and end."""

    grouped_input_fields = InputField.grouped_input_fields()

    breach = scenario.breaches.all()[0]
    scenariobreach = scenario.scenariobreach_set.get(breach=breach)

    data_objects = {
        'scenario': scenario,
        'project': scenario.project,
        'scenariobreach': scenariobreach,
        'breach': breach,
        'externalwater': breach.externalwater,
        'region': breach.region
        }

    for header in grouped_input_fields:
        for fieldobject in header['fields']:
            table = fieldobject.destination_table.lower()
            field = fieldobject.destination_field
            if table == 'extrascenarioinfo':
                info = ExtraScenarioInfo.get(
                    scenario=scenario, fieldname=field)
                if info is None:
                    fieldobject.value = None
                else:
                    fieldobject.value = info.value
            elif table in data_objects:
                field.value = getattr(data_objects[table], field, None)
            elif table == 'result':
                # We do these differently
                pass
            else:
                # Unknown, show it
                field.value = '{0}/{1}'.format(table, field)

        # Only keep fields with a value
        header['fields'] = [f for f in header['fields'] if f.value]

    # Only keep headers with fields
    grouped_input_fields = [h for h in grouped_input_fields if h['fields']]

    return render_to_response(
        'flooding/infowindow_information.html',
        {'grouped_fields': grouped_input_fields,
         'scenario_id': scenario.id})


def infowindow_information_old(scenario):
    """
    - Returns the information for in the infowindow
    - The information is collected from several tables in the database
    """

    breaches = scenario.breaches.all()

    # Get general information
    general_info_list = list()
    breach_names = ', '.join([b.name for b in breaches])
    region_names = ', '.join([b.region.name for b in breaches])

    general_info_list.append((_('Breach locations'), breach_names))
    general_info_list.append((_('Region'), region_names))
    general_info_list.append((_('Project'), scenario.project.friendlyname))

    general_info_list += scenario.get_scenario_overview_extra_info(
        ExtraInfoField.HEADER_GENERAL)

    # Get metadata information
    metadata_info_list = list()
    metadata_info_list.append((_('Scenario id'), scenario.id))
    metadata_info_list.append((_('Scenario remarks'), scenario.remarks))

    metadata_info_list += scenario.get_scenario_overview_extra_info(
        ExtraInfoField.HEADER_METADATA)

    attachment_list = list()

    inundationmodel_attachments = (
        scenario.sobekmodel_inundation.attachments.
        order_by('-uploaded_date'))
    scenario_attachments = (
        scenario.attachments.
        order_by('-uploaded_date'))
    project_attachments = (
        scenario.project.attachments.
        order_by('-uploaded_date'))

    sobekmodel_choices = []

    #Get the the sobekmodels
    for breach in breaches:
        for sobekmodel in breach.sobekmodels.all():
            sobekmodel_choices += [sobekmodel.id]

    breachmodel_attachments = Attachment.objects.filter(
        content_type=SobekModel,
        object_id__in=sobekmodel_choices
        ).order_by('-uploaded_date')

    scen_atts = [(f.file.name, os.path.split(f.file.name)[1])
                 for f in scenario_attachments]
    proj_atts = [(f.file.name, os.path.split(f.file.name)[1])
                 for f in project_attachments]
    inun_atts = [(f.file.name, os.path.split(f.file.name)[1])
                 for f in inundationmodel_attachments]
    brea_atts = [(f.file.name, os.path.split(f.file.name)[1])
                 for f in breachmodel_attachments]

    attachment_list.append((_('Scenario attachments'), scen_atts))
    attachment_list.append((_('Project attachments'), proj_atts))
    attachment_list.append((_('Inundationmodel attachments'), inun_atts))
    attachment_list.append((_('Externalwater model attachments'), brea_atts))

    #Get breach 'set' information
    breachset_info_list = list()

    for breach in breaches:
        #Get breach information
        scenariobreach = scenario.scenariobreach_set.get(breach=breach)

        breach_info_list = list()
        breach_info_list.append((_('Name'), breach.name))
        breach_info_list.append((_('Initial breach width'),
                                 scenariobreach.widthbrinit))
        breach_info_list.append(
            (_('Duration till breach has maximal depth'),
             get_intervalstring_from_dayfloat(scenariobreach.tmaxdepth)))
        breach_info_list += scenario.get_scenario_overview_extra_info(
            ExtraInfoField.HEADER_BREACH)

        #Get external water info
        extw_info_list = list()
        extw_info_list.append(
            (_('Externalwater name'), breach.externalwater.name))
        extw_info_list.append(
            (_('Externalwater type'),
             breach.externalwater.get_type_display()))
        if scenariobreach.manualwaterlevelinput:
            extw_info_list.append(
                (_('Maximal water level'), _('manual input used')))
            extw_info_list.append(
                (_('Repeating period duration'), _('manual input used')))
        else:
            extw_info_list.append(
                (_('Maximal water level'), scenariobreach.extwmaxlevel))
            extw_info_list.append(
                (_('Repeating period duration'),
                 scenariobreach.extwrepeattime))

        extw_info_list.append(
            (_('Bottom level breach'), scenariobreach.bottomlevelbreach))
        extw_info_list.append(
            (_('Pit depth'), scenariobreach.pitdepth))

        if breach.externalwater.type == ExternalWater.TYPE_SEA:
            if scenariobreach.manualwaterlevelinput:
                extw_info_list.append(
                    (_('Duration storm'), _('manual input used')))
                extw_info_list.append(
                    (_('Duration peak'), _('manual input used')))
                extw_info_list.append(
                    (_('Tide shift'), _('manual input used')))
            else:
                extw_info_list.append(
                    (_('Duration storm'),
                     get_intervalstring_from_dayfloat(scenariobreach.tstorm)))
                extw_info_list.append(
                    (_('Duration peak'),
                     get_intervalstring_from_dayfloat(scenariobreach.tpeak)))
                extw_info_list.append(
                    (_('Tide shift'),
                     get_intervalstring_from_dayfloat(
                            scenariobreach.tdeltaphase)))
            if scenariobreach.tide != None:
                extw_info_list.append(
                    (_('Tide properties'), scenariobreach.tide.name))
            if len(scenariobreach.waterlevelset.waterlevel_set.all()) > 0:
                image_src = (
                    reverse('flooding_service') +
                    "?action=get_externalwater_graph_infowindow&width=350&" +
                    "height=400&scenariobreach_id=" +
                    str(scenariobreach.id))
                extw_info_list.append(
                        (_('External water graph'),
                         '<img src="' + image_src +
                         ' " width=350 height=400/>'))
        elif breach.externalwater.type == ExternalWater.TYPE_LAKE:
            extw_info_list.append(
                        (_('Duration storm'),
                         get_intervalstring_from_dayfloat(
                        scenariobreach.tstorm)))
            extw_info_list.append(
                        (_('Duration peak'),
                         get_intervalstring_from_dayfloat(
                        scenariobreach.tpeak)))

        elif breach.externalwater.type == ExternalWater.TYPE_CANAL:
            pass
        elif breach.externalwater.type == ExternalWater.TYPE_INTERNAL_LAKE:
            pass
        elif breach.externalwater.type == ExternalWater.TYPE_INTERNAL_CANAL:
            pass
        elif breach.externalwater.type == ExternalWater.TYPE_RIVER:
            pass
        elif breach.externalwater.type == ExternalWater.TYPE_LOWER_RIVER:
            extw_info_list.append(
                (_('Duration storm'),
                 get_intervalstring_from_dayfloat(
                        scenariobreach.tstorm)))
            extw_info_list.append(
                (_('Duration peak'),
                 get_intervalstring_from_dayfloat(
                        scenariobreach.tpeak)))
            if scenariobreach.tide != None:
                extw_info_list.append(
                        (_('Tide properties'), scenariobreach.tide.name))

        extw_info_list += scenario.get_scenario_overview_extra_info(
            ExtraInfoField.HEADER_EXTERNALWATER)

        breachset_info_list.append(
            (breach.name, breach_info_list,
             breach.externalwater.name, extw_info_list))

    return render_to_response(
        'flooding/infowindow_information.html',
        {'general_info_list': general_info_list,
         'metadata_info_list': metadata_info_list,
         'breachset_info_list': breachset_info_list,
         'attachment_list': attachment_list,
         'scenario_id': scenario.id})


@login_required
def infowindow_remarks(request, scenario_id, callbackfunction, form_id):
    """Edits scenario name and remarks"""
    scenario = get_object_or_404(Scenario, pk=scenario_id)
    pm = PermissionManager(request.user)
    if not(pm.check_project_permission(
            scenario.project, UserPermission.PERMISSION_SCENARIO_EDIT_SIMPLE)):
        return HttpResponse(_("No permission to import scenario or login"))
    if request.method == 'POST':
        form = ScenarioNameRemarksForm(request.POST, instance=scenario)
        if form.is_valid():
            form.save()
    else:
        form = ScenarioNameRemarksForm(instance=scenario)
    return render_to_response('flooding/infowindow_remarks.html',
                              {'form': form,
                               'callbackfunction': callbackfunction,
                               'form_id': form_id})


def infowindow_approval(request, scenario_id, callbackfunction,
                        form_id, with_approvalobject):
    """Calls the page to give approval to scenarios"""

    used_scenario = get_object_or_404(Scenario, pk=scenario_id)

    pm = PermissionManager(request.user)
    if not(pm.check_project_permission(
            used_scenario.project,
            UserPermission.PERMISSION_SCENARIO_APPROVE)):
        return HttpResponse(_("No permission to import scenario or login"))

    if request.method == 'POST':
        form = TaskApprovalForm(request.POST)
        if form.is_valid():
            newTask = Task(scenario=used_scenario,
                           remarks=form.cleaned_data['remarks'],
                           tasktype=TaskType.objects.get(id=190),
                           tstart=datetime.datetime.now(),
                           tfinished=datetime.datetime.now(),
                           creatorlog=request.user.username
                           )
            # Convert string values to boolean (the None option, will
            # be handled correctly)
            if form.cleaned_data['successful'] == 'True':
                newTask.successful = True
            elif form.cleaned_data['successful'] == 'False':
                newTask.successful = False
            newTask.save()
    else:
        form = TaskApprovalForm()

    approved_tasks = Task.objects.filter(
        Q(scenario=used_scenario), Q(tasktype=TaskType.TYPE_SCENARIO_APPROVE))
    ordered_approved_tasks = approved_tasks.order_by('tfinished')

    if used_scenario.approvalobject and with_approvalobject:
        items = {}
        for label, value in request.REQUEST.items():
            items[label] = value

        items['callback'] = (
            'callbackFunctions["ApprovalObjectCallbackFormFunction"]()')
        items['formId'] = 'totalApprovalForm'
        url_args = '?' + string.join(["%s=%s" % x for x in items.items()], "&")

        destroy_function = request.REQUEST.get('destroy_function', None)
        create_function = request.REQUEST.get('create_function', None)
        pane_id = request.REQUEST.get('pane_id', None)
        return render_to_response(
            'flooding/infowindow_approval_total.html',
            {"approval_object": approvaltable(
                    request, used_scenario.approvalobject.id, True),
             'with_approval_object': True,
             'form': form,
             'ordered_approved_tasks': ordered_approved_tasks,
             'callbackfunction': callbackfunction,
             'form_id': form_id,
             'url_args': url_args,
             'destroy_function': destroy_function,
             'create_function': create_function,
             'pane_id': pane_id
             })

    else:
        return render_to_response(
            'flooding/infowindow_approval.html',
            {'form': form,
             'ordered_approved_tasks': ordered_approved_tasks,
             'callbackfunction': callbackfunction,
             'form_id': form_id})


def infowindow_edit(request, scenario_id):
    used_scenario = get_object_or_404(Scenario, pk=scenario_id)
    pm = PermissionManager(request.user)
    if not(pm.check_project_permission(
            used_scenario.project, UserPermission.PERMISSION_SCENARIO_EDIT)):
        return HttpResponse(_("No permission to import scenario or login"))

    return render_to_response(
        'flooding/infowindow_edit.html',
        {'scenario_id': scenario_id})


def showattachments(request, scenario_id):
    """Calls the page to give approval to scenarios"""
    succeeded = False
    sobekmodel_choices = []
    object_name_and_path_map = {
        'inundationmodel': (_('Inundation model'),
                            Template('inundationmodels/$id/')),
        'breachmodel': (_('Sobek models'), Template('sobekmodels/$id/')),
        'scenario': (_('Scenario'), Template('scenarios/$id/')),
        'project': (_('Project'), Template('projects/$id/'))}

    used_scenario = get_object_or_404(Scenario, pk=scenario_id)
    request_related_to = request.REQUEST.get('relatedto')

    if request_related_to == 'inundationmodel':
        attachments = used_scenario.sobekmodel_inundation.attachments.order_by(
            'uploaded_date').reverse()
        related_to_object = used_scenario.sobekmodel_inundation
    elif request_related_to == 'breachmodel':
        #Get contenttype of the sobekmodel.
        #Needed for generic relation search for multiple breaches
        c = ContentType.objects.get(model='sobekmodel')

        #Get the the sobekmodels
        for breach in used_scenario.breaches.all():
            for sobekmodel in breach.sobekmodels.all():
                sobekmodel_choices += [[
                        sobekmodel.id,
                        (sobekmodel.get_sobekmodeltype_display() +
                         ' : ' + str(sobekmodel.sobekversion))]]

        #Get the attachments of all sobekmodels related to this scenario
        attachments = Attachment.objects.filter(
            content_type=c,
            object_id__in=[sm[0] for sm in sobekmodel_choices]
            ).order_by('uploaded_date')
    elif request_related_to == 'scenario':
        attachments = used_scenario.attachments.order_by(
            'uploaded_date').reverse()
        related_to_object = used_scenario
    elif request_related_to == 'project':
        attachments = used_scenario.project.attachments.order_by(
            'uploaded_date').reverse()
        related_to_object = used_scenario.project

    if request.method == 'POST':

        form = AttachmentForm(sobekmodel_choices, request.POST, request.FILES)
        if form.is_valid():
            if 'Sobekmodel' in form.cleaned_data:
                related_to_object = SobekModel.objects.get(
                    pk=int(form.cleaned_data['Sobekmodel']))

            newAttachment = Attachment(
                uploaded_by=request.user.username,
                uploaded_date=datetime.datetime.now(),
                content_object=related_to_object,
                content_type=ContentType.objects.get_for_model(
                    related_to_object),
                object_id=related_to_object.id,
                file=None,
                name=form.cleaned_data['name'],
                remarks=form.cleaned_data['remarks'])

            # got it only working with creating explicitly the
            # contentfile and saving it as the 'file' of the
            # 'newAttachment'
            file_content = ContentFile(request.FILES['file'].read())
            newAttachment.file.save(request.FILES['file'].name, file_content)
            newAttachment.save()
            succeeded = True
    else:
        form = AttachmentForm(sobekmodel_choices)

    related_to = object_name_and_path_map[request_related_to][0]
    action_url = ('/flooding/infowindow/?scenarioid=' + scenario_id +
                  '&action=showattachments&relatedto=' + request_related_to)
    return render_to_response(
        'flooding/showattachments.html', {
            'form': form,
            'succeeded': succeeded,
            'related_to': related_to,
            'attachments': attachments,
            'scenario_id': scenario_id,
            'action_url': action_url})


def editproperties(request, scenario_id):
    """ Renders the page for editing properties of the scenario

    For this method the right permissions are required

    """
    used_scenario = get_object_or_404(Scenario, pk=scenario_id)
    pm = PermissionManager(request.user)
    if not(pm.check_project_permission(
            used_scenario.project, UserPermission.PERMISSION_SCENARIO_EDIT)):
        return HttpResponse(_("No permission to import scenario or login"))

    succeeded = False
    if request.method == "POST":
        form = EditScenarioPropertiesForm(request.POST)
        if form.is_valid():
            cleaned_animation_start = form.cleaned_data['animation_start']
            scenario_breaches = ScenarioBreach.objects.filter(
                scenario=used_scenario)
            for sb in scenario_breaches:
                #tstartbreach is in days, but input in hours
                sb.tstartbreach = float(cleaned_animation_start) / 24
                sb.save()
            for pl in used_scenario.presentationlayer.all():
                animation = Animation.objects.filter(presentationlayer=pl)
                if animation.count() > 0:
                    # the model guarantees that there is only one animation
                    anim = animation[0]  # needed for correct saving
                                         # (weird thing in
                                         # Django... (JMV))
                    anim.startnr = cleaned_animation_start
                    anim.save()
            succeeded = True
    else:
        scenario_breaches = ScenarioBreach.objects.filter(
            scenario=used_scenario)
        #tstartbreach is in days, but input in hours
        min_value = min([int(round(sb.tstartbreach * 24))
                         for sb in scenario_breaches])
        form = EditScenarioPropertiesForm({'animation_start': min_value})

    return render_to_response('flooding/edit_scenario_properties.html',
                              {'scenario': used_scenario,
                               'form': form,
                               'succeeded': succeeded})
