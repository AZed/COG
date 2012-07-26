from cog.models import *
from cog.models.utils import site_index
from cog.views import encodeMembershipPar, NEW_MEMBERSHIP, OLD_MEMBERSHIP, NO_MEMBERSHIP
from cog.views import userCanPost, userCanView
from django import template
from django.core.urlresolvers import reverse
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
import re
from cog.utils import smart_truncate, INVALID_CHARS
from django.conf import settings
from cog.models.constants import DEFAULT_LOGO, FOOTER_LOGO

register = template.Library()

@register.filter
def concat(astring, bstring):
    return str(astring) + str(bstring)

@register.filter
def dictKeyLookup(the_dict, key):
   # Try to fetch from the dict, and if it's not found return an empty string.
   return the_dict.get(key, '')

# Utility function to set the "escape" function to be conditional_escape, or the identity function
# depending on the auto-escape context currently in effect in the template.
# conditional_escape does not escape instances of SafeData
def get_escape_function(autoescape):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return esc

# filter that builds the hierarchy tree for the current project
@register.filter
def tree_this_project(user, project, autoescape=None):
    
    html = project_tree(user, project, autoescape, 1)
            
    # mark the result as safe from further escaping
    return mark_safe(html)

tree_this_project.needs_autoescape = True

# filter that builds a flat list of all projects
@register.filter
def tree_all_projects(user, autoescape=None):
      
    # retrieve all active projects
    projects = Project.objects.filter(active=True).order_by('short_name')
    
    return projects_tree(user, projects, autoescape, "treeDivAll")

tree_all_projects.needs_autoescape = True

# filter that builds a flat list of projects the user is member of
@register.filter
def tree_my_projects(user, autoescape=None):
            
    if user.is_authenticated():
        
        # retrieve all active projects
        projects = getProjectsForUser(user, False) # includePending==False
        
        return projects_tree(user, projects, autoescape, "treeDivMy")
    
    else:
        html = "<i>Please login to display your projects.</i>"
    
        # mark the result as safe from further escaping
        return mark_safe(html)

tree_my_projects.needs_autoescape = True

# function to build the HTML for a flat list of projects
def projects_tree(user, projects, autoescape, treeId):

    if len(projects) > 0:    
        esc = get_escape_function(autoescape)
    
        html = "<div id='project_tree_all_%s' class='yui-skin-sam'>" % treeId
        # no check boxes to select projects
        # use class ygtv-highlight1 because it doesn't show any blue background when selected
        html += "<div id='%s' class='ygtv-highlight1'>" % treeId
        #html += "<div id='%s' class='ygtv-checkbox'>" % treeId
        html += "<ul>"
        # loop over all projects
        for project in projects:
            if project.isVisible(user):
                html += "<li><span class='%s'><a href='%s'>%s</a></span>" % ('child', reverse('project_home',args=[project.short_name.lower()]), esc(project.short_name))
        html += "</ul>"
        html += "</div>"
        html += "</div>"
        
        # fire java-script event to initialize the tree object
        html += "<script>YAHOO.util.Event.onContentReady('%s', treeInit, this);</script>" % treeId
    
    # empty list
    else:
        html = "<i>No projects found.</i>"
    
    # mark the result as safe from further escaping
    return mark_safe(html)

# function to build the hierarchy tree for any given project
def project_tree(user, project, autoescape, i):
    
    esc = get_escape_function(autoescape)
    
    treeId = "treeDiv%s" % i
    html = "<div id='project_tree_%s' class='yui-skin-sam'>" % i
    if hasUserPermission(user, project):
        # show checkboxes to select projects in the tree
        html += "<div id='%s' class='ygtv-checkbox'>" % treeId
    else:
        # use class ygtv-highlight1 because it doesn't show any blue background when selected
        html += "<div id='%s' class='ygtv-highlight1'>" % treeId
    if project.parent:
        html += "<ul><li class='expanded'><span class='parent'><a href='%s'>%s</a></span>" \
        % (reverse('project_home',args=[project.parent.short_name.lower()]),esc(project.parent.short_name))
    html += "<ul>"
    # expand first child
    html += _project_tree(user, project, esc, expanded=True, dopeers=True, icon='this')
    html += "</ul>"
    if project.parent:
        html += "</li></ul>"
    html += "</div>"
    html += "</div>"
    
    # fire java-script event to initialize the tree object
    html += "<script>YAHOO.util.Event.onContentReady('%s', treeInit, this);</script>" % treeId
    
    return html

@register.filter
def index(project):
    return site_index(project)
    
# filter to list the bookmarks folders for a user, project combination
@register.filter
def list_bookmarks(project, user, autoescape=None):
    
    folder = getTopFolder(project)
    
    esc = get_escape_function(autoescape)
    treeId = project.short_name+"folderTree"
    
    html = "<div id='folder_tree' class='yui-skin-sam'>" 
    html += "<div id='%s'>" % treeId
   
    # start recursion from this folder
    html += "<ul>"
    html += _folder_tree(folder, user, esc, expanded=True, icon='folder') # expand this folder and its children
    html += "</ul>"

    html += "</div>"
    html += "</div>"
    
    # fire java-script event to initialize the tree object
    html += "<script>YAHOO.util.Event.onContentReady('%s', bookmarkTreeInit, this);</script>" % treeId    
    
    # mark the result as safe from further escaping
    return mark_safe(html)

list_bookmarks.needs_autoescape = True


# recursive function to build the folder hierarchy tree
def _folder_tree(folder, user, esc, expanded=False, icon='folder'):
    
    static_url = getattr(settings, "STATIC_URL", "static/")
   
    # this folder 
    if expanded:
        html = "<li class='expanded'>"
    else:
        html = "<li>"
    html += "<span class='%s'>%s" % (icon, folder.name)
    
    # add edit/delete links, but not to top level folder
    if folder.parent:
        deleteurl = reverse('folder_delete', args=[folder.id])
        updateurl = reverse('folder_update', args=[folder.id])
        if hasUserPermission(user, folder.project):
            html += "&nbsp;&nbsp;[ <a href='"+updateurl+"' class='changelink'>Edit</a> | "
            html += "<a href='"+deleteurl+"' class='deletelink' onclick=\"return urlConfirmationDialog('Delete Folder Confirmation'," \
                 + "'Are you sure you want to delete this folder (including all the bookmarks and folders it contains) ?', this)\">Delete</a> ]"
    html += "</span> "
   
    # this folder's children
    if folder.children() or folder.bookmark_set.all():
        html += "<ul>"
                
        # display bookmarks
        for bookmark in folder.bookmark_set.all():
            deleteurl = reverse('bookmark_delete', args=[bookmark.id])
            updateurl = reverse('bookmark_update', args=[bookmark.id])
            html += "<li><span class='bookmark'>"
            html += "<a href='%s'>%s</a>"  % (bookmark.url, bookmark.name)
            # display [Edit|Delete] links
            if hasUserPermission(user, folder.project):
                html += "&nbsp;&nbsp;[ <a href='"+updateurl+"' class='changelink'>Edit</a> | "
                html += "<a href='"+deleteurl+"' class='deletelink' onclick=\"return urlConfirmationDialog('Delete Bookmark Confirmation','Are you sure you want to delete this bookmark ?', this)\">Delete</a> ]"
            # display "Notes" link
            if bookmark.notes:
                html += "&nbsp;&nbsp;[ <img src='%scog/img/notes_16x16.png' style='vertical-align:bottom;' /><a href='%s'> Notes</a> ]" % (static_url, reverse('post_detail', args=[bookmark.notes.id]))
            if bookmark.description:
                html += "<br/>%s<br/>" % bookmark.description
            html += "</span></li>"
                        
        # display sub-folders
        for child in folder.children():
            
            # recursion (do not expand children)
            html += _folder_tree(child, user, esc, expanded=False) 

        html += "</ul>"
    
    html += "</li>"
        
    return html

# Filter to return a simple list of bookmark folders for a project, user combination
# The filter is composed of tuples of the form (folder object, folder hierarchy label)
@register.filter
def listFolders(project, user):

    folders = []
    _listSubfolders( getTopFolder(project), '', folders)
    return folders

def _listSubfolders( folder, hierarchy_label, folders):
    # add parent folder, append its name to hierarchy label
    hierarchy_label = "%s %s" % (hierarchy_label, folder.name)
    # truncate the folder hierarchy names to 100 characters
    folders.append( (folder, smart_truncate(hierarchy_label, 100)) )
    #folders.append( folder )
    # recursion over children
    for subFolder in folder.children():
        _listSubfolders( subFolder, "%s >" % hierarchy_label, folders)

# Filter that returns the top-level folder for a given project.
@register.filter
def getTopFolderForProject(project):
    return getTopFolder(project)
    
# recursive function to build the project hierarchy tree
def _project_tree(user, project, esc, expanded=False, dopeers=False, icon='child'):
   
    if project.isNotVisible(user):
        return ""
    
    # this project 
    #if icon=='this':
    #     html = "<li class='expanded' yuiConfig='{\"checked\":\"yes\"}'>"
    if expanded:
        html = "<li class='expanded'>"
    else:
        html = "<li>"
    html += "<span class='%s'><a href='%s'>%s</a></span>" % (icon, reverse('project_home',args=[project.short_name.lower()]), esc(project.short_name))
    
    # this project's children
    if project.children:
        html += "<ul>"
        for child in project.children():
                # recursion (do not expand children and do not retrieve their peers)
                html += _project_tree(user, child, esc) 
        html += "</ul>"
    html += "</li>"
    
    # this project's peers
    if dopeers and project.peers.all():
        for peer in project.peers.all():
                html += _project_tree(user, peer, esc, icon='peer')
        
    return html

# filter that embeds words starting with http(s) in HTML <a> tags
@register.filter
def textToHtml(text, autoescape=None):
    
    p = re.compile('(https*://[^\s]+)', re.IGNORECASE)
    esc = get_escape_function(autoescape)
    esctext = esc(text)
    
    html = p.sub('<a href="\g<1>">\g<1></a>', esctext)
    
    return mark_safe(html)
    
textToHtml.needs_autoescape = True


# filter to determine whether a user is enrolled in a group
@register.filter
def isEnrolled(user, group):
    if group in user.groups.all():
        return True
    else:
        return False
    
# filter to determine whether a user belongs to a project
@register.filter
def hasUser(project, user):
    return project.hasUser(user)
    
# filter to determine whether a user is pending approval in a project
@register.filter
def hasUserPending(project, user):
  return project.hasUserPending(user)  
    
# filters to encode a membership HTTP parameter
@register.filter
def newMembership(group, user):
    return encodeMembershipPar(NEW_MEMBERSHIP, group.name, user.id)

@register.filter
def oldMembership(group, user):
    return encodeMembershipPar(OLD_MEMBERSHIP, group.name, user.id)

@register.filter
def noMembership(group, user):
    return encodeMembershipPar(NO_MEMBERSHIP, group.name, user.id)

@register.filter
def hasUserPermission(user, project):
    return userHasUserPermission(user, project)

@register.filter
def hasAdminPermission(user, project):
    return userHasAdminPermission(user, project)

@register.filter
def canPost(user, post):
    return userCanPost(user, post)

@register.filter
def relatedPostCount(post):
    count = len(post.post_set.all())
    if post.parent:
        count += 1
    return count

@register.filter
def numberOptions(lastNumber, selectedNumber):
    lastNumberPlusOne = int(lastNumber)
    selectedNumber = int(selectedNumber)
    html = ""
    for n in range(1, lastNumber+1):
        html += "<option value='%d'" % n
        if n==selectedNumber:
            html += "selected='selected'"
        html += ">%d</option>" % n
    # mark the result as safe from further escaping
    return mark_safe(html)
    
# Utility method to return a list of active project tabs
@register.filter
def getTopNav(project):
        
    tabs = []
    ptabs = get_or_create_project_tabs(project, save=True)
    for ptab in ptabs:
        if ptab.active:
            tabs.append( (ptab.label, ptab.url) )
            
    return tabs

@register.filter
def selectedTabStyle(request, tab):
    # selected tab
    if request.path==tab[1]:
        return mark_safe("style='color:#358C92; background-color: #FFFFFF'")
    # unselected tab
    else:
        return ""
    
# Utility method to return the list of invalid characters
@register.filter
def getInvalidCharacters(project):
    return "!@#$%^&*[]/{}|\"\\<>"
    # remove leading [ and trailing \]
    #return INVALID_CHARS[1:len(INVALID_CHARS)-1]
    
# filter that inserts a lock icon if the user can not view the URL
@register.filter
def is_locked(post, request, autoescape=None):
     
    # show lock depending on user authentication status and permissions       
    #if userCanView(request.user, post):
    #    html = ""
    #else:
    #    html = "&nbsp;<span class='privatelink'>&nbsp;</span>"
    
    # show lock depending on page properties
    if post.is_private:
        html = "&nbsp;<span class='privatelink'>&nbsp;</span>"
    else:
        html = ""
            
    # mark the result as safe from further escaping
    return mark_safe(html)

@register.filter
def getDefaultLogo(request):
    return getattr(settings, "STATIC_URL", "") + DEFAULT_LOGO

@register.filter
def getFooterLogo(request):
    return getattr(settings, "STATIC_URL", "") + FOOTER_LOGO

@register.filter
def get_form_global_errors(form):
    errors = dict(form.errors)
    return list(errors.get("__all__", []))

@register.filter
def get_organizational_roles(project, category):
        
    return getOrganizationalRoles(project, category)

@register.filter
def get_management_bodies(project, category):
        
    return getManagementBodies(project, category)

@register.filter
def is_home_page(request, project):
    
    if project.home_page_url() == request.path:
        return True
    else:
        return False
    