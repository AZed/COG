from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse

from cog.models import *
from cog.forms import *
from constants import PERMISSION_DENIED_MESSAGE
    
def news_list(request, project_short_name):
    
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
   
    return render_to_response('cog/news/news_list.html', 
                              {'project': project, 
                               'title': '%s News' % project.short_name,
                               'project_news': project.news() }, 
                               context_instance=RequestContext(request))
    
def news_detail(request, news_id):
    
    news = get_object_or_404(News, pk=news_id)
    
    return render_to_response('cog/news/news_detail.html', 
                              {'project': news.project, 
                               'news': news,
                               'title': '%s News' % news.title },
                               context_instance=RequestContext(request))
    
@login_required
def news_update(request, news_id):
    
    news = get_object_or_404(News, pk=news_id)
    
    # check permission
    if not userHasUserPermission(request.user, news.project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)

    # GET method pre-populates the form with the news properties    
    if (request.method=='GET'):
                            
        # create form from instance
        form = NewsForm(instance=news)
        return render_news_form(request, request.GET, form, news.project)
    
    # POST method saves the modified instance    
    elif (request.method=='POST'):
        
        # update existing database model with form data
        form = NewsForm(request.POST, instance=news)
        if (form.is_valid()):
            news = form.save()
            
            # redirect to project home (GET-POST-REDIRECT)
            return HttpResponseRedirect(reverse('project_home', args=[news.project.short_name.lower()]))
        
        # invalid data
        else:
            print "Form is invalid: %s" % form.errors
            news = form.instance
            return render_news_form(request, request.POST, form, news.project)

    
@login_required
def news_add(request, project_short_name):
    
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check permission
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
        
    # GET method pre-populates the form from the request parameters    
    if (request.method=='GET'):
        
        # create empty News object
        news = News()

        # set main project
        news.project = project
                    
        # create form from (unsaved) instance
        form = NewsForm(instance=news)
        return render_news_form(request, request.GET, form, news.project)
        
    # POST method validates the form data and saves instance to database
    else:
        
        # create form object from form data
        form = NewsForm(request.POST)
                
        if form.is_valid():

            # save object to the database - including the m2m relations to other projects
            news = form.save()
            # redirect to project home (GET-POST-REDIRECT)
            return HttpResponseRedirect(reverse('project_home', args=[news.project.short_name.lower()]))
        
        # invalid data
        else:
            #print "Form is invalid: %s" % form.errors
            news = form.instance
            return render_news_form(request, request.POST, form, news.project)
        
@login_required
def news_delete(request, news_id):
    
    news = get_object_or_404(News, pk=news_id)
    project = news.project
    
    # check permission
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    # show confirmation form
    if (request.method=='GET'):
        return render_to_response('cog/news/news_delete.html', 
                                  {'news': news, 'project':project, 'title': 'Delete News' },
                                  context_instance=RequestContext(request))
        
    # execute, and redirect to project's home page
    else:
        news.delete()
        # redirect to project home (GET-POST-REDIRECT)
        return HttpResponseRedirect(reverse('project_home', args=[project.short_name.lower()]))

        

            
# function to extract the other projects from the GET/POST request parameters
def get_other_projects(qdict, method):
    other_projects_refs =  qdict.getlist('other_projects')
    other_projects = []
    for ref in other_projects_refs:
        if (method=='GET'):
            other_project = get_object_or_404(Project, short_name=ref)
        else:
            other_project = get_object_or_404(Project, id=ref)
        other_projects.append(other_project)
    return other_projects
    
def render_news_form(request, qdict, form, project):
 
    return render_to_response('cog/news/news_form.html', 
                              {'form': form, 'title': 
                               'Publish %s News' % project.short_name,
                               'project' : project,
                               'other_projects' : get_other_projects(qdict, request.method) }, 
                               context_instance=RequestContext(request))
    