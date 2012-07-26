from django.shortcuts import get_object_or_404, render_to_response
from cog.models import *
from django.contrib.auth.models import User
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from cog.forms import *
from django.http import HttpResponseRedirect
from django.http import HttpResponse  
from django.forms.models import modelformset_factory
from constants import PERMISSION_DENIED_MESSAGE
from cog.models.constants import TYPE_TRACKER, TYPE_CODE, TYPE_POLICY, TYPE_ROADMAP
from views_project import getProjectNotActiveRedirect, getProjectNotVisibleRedirect

# View to display the project trackers.
def trackers_display(request, project_short_name):
        
    return external_urls_display(request, project_short_name, TYPE_TRACKER, 'cog/project/trackers.html', 'Trackers')

# View to display the project code URLs.
def code_display(request, project_short_name):
        
    return external_urls_display(request, project_short_name, TYPE_CODE, 'cog/project/code.html', 'Code')

# View to display the project roadmap.
def roadmap_display(request, project_short_name):
        
    return external_urls_display(request, project_short_name, TYPE_ROADMAP, 'cog/project/roadmap.html', 'Roadmap')

    
# Generic view to display a given type of external URLs.
# This view sub-selects the project peer and children that external URLs of that type, 
# so that the page can render the widgets only if the URLs are found.
def external_urls_display(request, project_short_name, external_url_type, template, title):
    
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check project is active
    if project.active==False:
        return getProjectNotActiveRedirect(request, project)
    elif project.isNotVisible(request.user):
        return getProjectNotVisibleRedirect(request, project)

    
    # build list of children with trackers
    children = []
    for child in project.children():
        if len(child.get_external_urls(external_url_type)) > 0 and child.isVisible(request.user):
            children.append(child)
    
    # build list of peers with trackers
    peers = []
    for peer in project.peers.all():
        if len(peer.get_external_urls(external_url_type)) > 0 and peer.isVisible(request.user):
            peers.append(peer)
        
    return render_to_response(template, 
                              {'title' : '%s %s' % (project.short_name, title), 
                               'project':project, 'peers' : peers, 'children': children },
                               context_instance=RequestContext(request))
    
# View to update the project trackers
@login_required
def trackers_update(request, project_short_name):
    
    type = TYPE_TRACKER
    redirect = reverse('trackers_display', args=[project_short_name])
    return external_urls_update(request, project_short_name, type, redirect)

# View to update the project code
@login_required
def code_update(request, project_short_name):
    
    type = TYPE_CODE
    redirect = reverse('code_display', args=[project_short_name])
    return external_urls_update(request, project_short_name, type, redirect)

# View to update the project roadmap
@login_required
def roadmap_update(request, project_short_name):
    
    type = TYPE_ROADMAP
    redirect = reverse('roadmap_display', args=[project_short_name])
    return external_urls_update(request, project_short_name, type, redirect)

# View to update the project policies
@login_required
def policies_update(request, project_short_name):
    
    type = TYPE_POLICY
    redirect = reverse('governance_display', args=[project_short_name])
    return external_urls_update(request, project_short_name, type, redirect)

# Generic view to update external URLs
@login_required
def external_urls_update(request, project_short_name, type, redirect):
    
    # load user from session, project from HTTP request
    user = request.user
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check permission
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    # number of empty instances to be displayed
    # exclude fields 'project', 'type' so they don't get validated
    # allow for instances to be deleted
    nextras = 1
    ExternalUrlFormSet = modelformset_factory(ExternalUrl, extra=nextras, exclude=('project','type'), can_delete=True)
    
    # GET
    if request.method=='GET':
        
        # create formset instance backed by current saved instances
        # must provide the initial data to all the extra instances, 
        # which come in the list after the database instances
        #queryset = ExternalUrl.objects.filter(project=project, type=type)
        #initial_data = [ {'project':project, 'type':type } for count in xrange(len(queryset)+nextras)]
        #formset = ExternalUrlFormSet(queryset=queryset,initial=initial_data)   
        formset = ExternalUrlFormSet(queryset=ExternalUrl.objects.filter(project=project, type=type))
        
        return render_external_urls_form(request, project, formset, type)
    
    # POST
    else:
        
        formset = ExternalUrlFormSet(request.POST)
        
        if formset.is_valid():
            # select instances that have changed, don't save to database yet
            instances = formset.save(commit=False)
            for instance in instances:
                instance.project = project
                instance.type = type
                instance.save()
            return HttpResponseRedirect(redirect)
        
        else:
            print formset.errors
            return render_external_urls_form(request, project, formset, type)
     
def render_external_urls_form(request, project, formset, type):
     return render_to_response('cog/project/external_urls_form.html', 
                              {'project':project, 'formset':formset, 'title' : '%s Update' % str.capitalize(type), 'type' : type },
                                context_instance=RequestContext(request))