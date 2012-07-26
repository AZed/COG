from django.shortcuts import get_object_or_404, render_to_response
from cog.models import *
from django.contrib.auth.models import User
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from cog.forms.forms_bookmarks import *
from django.http import HttpResponseRedirect
from django.utils import simplejson  
from django.http import HttpResponse  
from constants import PERMISSION_DENIED_MESSAGE, BAD_REQUEST
from views_project import getProjectNotActiveRedirect, getProjectNotVisibleRedirect
from views_post import post_add

def _hasBookmarks(project):
    """Function to determine whether a project has associated bookmarks."""
    
    bookmarks = Bookmark.objects.filter(folder__project=project)
    if len(bookmarks.all())>0:
        return True
    else:
        return False
    
# view to list the project bookmarks
def bookmark_list(request, project_short_name):
    
    # load the project
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # check project is active
    if project.active==False:
        return getProjectNotActiveRedirect(request, project)
    elif project.isNotVisible(request.user):
        return getProjectNotVisibleRedirect(request, project)
    
    # get or create top-level folder
    folder = getTopFolder(project)
    
    # build list of children with bookmarks that are visible to user
    children = []
    for child in project.children():
        if _hasBookmarks(child) and child.isVisible(request.user):
            children.append(child)
    
    # build list of peers with bookmarks that are visible to user
    peers = []
    for peer in project.peers.all():
        if _hasBookmarks(peer) and peer.isVisible(request.user):
            peers.append(peer)
                      
    # return to view
    return render_to_response('cog/bookmarks/bookmark_list.html', 
                              {'project':project, 'peers' : peers, 'children': children, 
                               'title': '%s Bookmarks' % project.short_name},
                               context_instance=RequestContext(request))
    
# View to add a bookmark via a standard web form
@login_required
def bookmark_add(request, project_short_name):
            
    # load user from session, project from HTTP request
    user = request.user
    
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)

    if request.method=='GET':
        
        # create unbounded form object
        form = BookmarkForm(project)
        
        # return to view
        return render_bookmark_form(request, project, form) 
        
    else:
        
        # create form object from form data
        form = BookmarkForm(project, request.POST)
        
        if form.is_valid():
            bookmark = form.save()
            
            # redirect to bookmarks listing
            return HttpResponseRedirect(reverse('bookmark_list', args=[project.short_name.lower()]))
                          
        else:
            print 'Form is invalid: %s' % form.errors
            return render_bookmark_form(request, project, form) 
                            
    return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')    

# View to add a bookmark via an ajax call through a pop-up window
@login_required
def bookmark_add2(request, project_short_name):
            
    # load user from session, project from HTTP request
    user = request.user
    
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)

    response_data = {}
    response_data['errors'] = {}
    if request.method=='POST':
    
        # create form object from form data
        form = BookmarkForm(project, request.POST)
        
        if form.is_valid():
            bookmark = form.save()
            response_data['result'] = 'Success'
            response_data['message'] = 'Your bookmark was saved.'
                                      
        else:
            print 'Form is invalid: %s' % form.errors
            # encode errors in response - although not used
            for key, value in form.errors.items():
                response_data['errors'][key] = value           
            response_data['result'] = 'Error'
            response_data['message'] = 'Sorry, the form data is invalid: %s' % form.errors

    else:
        response_data['result'] = 'Error'
        response_data['message'] = 'Sorry, the GET method is not supported'
                
    return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')    

# View to delete a bookmark
@login_required
def bookmark_delete(request, bookmark_id):
    
    bookmark = get_object_or_404(Bookmark, pk=bookmark_id)
    project = bookmark.folder.project
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
        
    # delete notes (recursively)
    if bookmark.notes:
        bookmark.notes.delete()
        
    # delete bookmark
    bookmark.delete()
    
    # redirect to bookmark listing
    return HttpResponseRedirect(reverse('bookmark_list', args=[project.short_name.lower()]))

# View to update a bookmark
@login_required
def bookmark_update(request, bookmark_id):
    
    bookmark = get_object_or_404(Bookmark, pk=bookmark_id)
    project = bookmark.folder.project
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
        
    if request.method=='GET':
        # create form object from model
        form = BookmarkForm(project, instance=bookmark)
        # return to view
        return render_bookmark_form(request, project, form) 

    else:
        
        # create form object from form data
        form = BookmarkForm(project, request.POST, instance=bookmark)
        
        if form.is_valid():
            
            bookmark = form.save()
            
            # redirect to bookmark listing
            return HttpResponseRedirect(reverse('bookmark_list', args=[project.short_name.lower()] ))
            
        else:
            print "Form is invalid: %s" % form.errors
            # return to view
            return render_bookmark_form(request, project, form)  
    
    
@login_required
def folder_add(request, project_short_name):
    
    # retrieve project from request, user from session
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    user = request.user
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    if request.method=='GET':
        
        # create empty Folder object, pre-populate project and user
        folder = Folder()
        folder.project = project
        
        # get or create top-level folder
        topfolder = getTopFolder(project)
        folder.parent = topfolder
                     
        # create form from instance
        # project, user are used to sub-select the parent folder options
        form = FolderForm(project, instance=folder)
        return render_folder_form(request, project, form)
    
    else:
        
        # create form object from form data
        form = FolderForm(project, request.POST)
        
        if form.is_valid():
            
            folder = form.save()
            
            # redirect to bookmark listing
            return HttpResponseRedirect(reverse('bookmark_list', args=[project.short_name.lower()] ))
            
        else:
            # return to view
            print "Form is invalid: %s" % form.errors
            return render_folder_form(request, project, form) 

@login_required
def folder_update(request, folder_id):
    
    # retrieve folder from request
    folder = get_object_or_404(Folder, pk=folder_id)
    
    # security check
    if not userHasUserPermission(request.user, folder.project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)

    if request.method=='GET':
        form = FolderForm(folder.project, instance=folder)
        return render_folder_form(request, folder.project, form)
    
    else:
        # create form object from form data
        form = FolderForm(folder.project, request.POST, instance=folder)
        
        if form.is_valid():
            
            folder = form.save()
            
            # redirect to bookmark listing
            return HttpResponseRedirect(reverse('bookmark_list', args=[folder.project.short_name.lower()]))
            
        else:
            # return to view
            print "Form is invalid: %s" % form.errors
            return render_folder_form(request, folder.project, form) 

@login_required
def folder_delete(request, folder_id):
    
    # retrieve folder from request
    folder = get_object_or_404(Folder, pk=folder_id)
    project = folder.project
    
    # security check
    if not userHasUserPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
        
    # delete folder and all of its content
    delete_folder(folder)
    
    # redirect to bookmark listing
    return HttpResponseRedirect(reverse('bookmark_list', args=[project.short_name.lower()] ))

# utility function to recursively delete each folder
# together with its content
def delete_folder(folder):
    
    # invoke recursion first
    for child in folder.children():
        delete_folder(child)
    
    # delete folder bookmarks
    for bookmark in folder.bookmark_set.all():
        print 'Deleting bookmark=%s' % bookmark
        bookmark.delete()

    # delete this folder
    print 'Deleting folder=%s' % folder
    folder.delete()

def render_folder_form(request, project, form):
    return render_to_response('cog/bookmarks/folder_form.html', 
                               {'project':project, 'form':form, 'title':'Bookmark Folder Form' },
                               context_instance=RequestContext(request))
    
def render_bookmark_form(request, project, form):
    return render_to_response('cog/bookmarks/bookmark_form.html', 
                              {'project':project, 'form':form, 'title':'Bookmark Form' },
                              context_instance=RequestContext(request))     
    
@login_required
def bookmark_add_notes(request, bookmark_id):
    
    # bookmark object
    bookmark = get_object_or_404(Bookmark, pk=bookmark_id)
    
    # project context
    project = bookmark.folder.project
    
    # invoke generic view
    #return add_notes(request, project, bookmark)
    return post_add(request, project.short_name, owner=bookmark)