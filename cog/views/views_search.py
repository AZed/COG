from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from cog.forms.forms_search import *
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.utils import simplejson 
import urllib, urllib2


from cog.views.constants import PERMISSION_DENIED_MESSAGE
from cog.services.search import SolrSearchService, TestSearchService
from cog.models.search import SearchOutput, Record, Facet, FacetProfile
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from copy import copy, deepcopy
from urllib2 import HTTPError

from cog.models.search import *
from cog.services.search import TestSearchService, SolrSearchService
from cog.services.SolrSerializer import deserialize


SEARCH_INPUT = "search_input"
SEARCH_OUTPUT = "search_output"
FACET_PROFILE = "facet_profile"
ERROR_MESSAGE = "error_message"
SEARCH_DATA = "search_data"

# singleton instance - instantiated only once
testSearchService = TestSearchService()

# method to configure the search on a per-request basis
def getTestSearchConfig(request):
    """
    Example of search configuration method that ties into a test search service and associated facets,
    and sets one fixed constraint.
    """
        
    facetProfile = FacetProfile([ 
                                 #('project','Project'),
                                 ('model','Model'),
                                 ('experiment','Experiment'),
                                 ('instrument','Instrument'),
                                 ])
    fixedConstraints = { 'project': ['Test Project'], }
    
    return SearchConfig(facetProfile, fixedConstraints, testSearchService)

def search(request):
    """
    Default view entry point that configures the search with a test search configuration.
    """
    
    config = getTestSearchConfig(request)
    return search_config(request, config)

def search_config(request, searchConfig, extra={}):
    """
    View entry point for applications that need to provide their own
    per-request search configuration.
    """
    
    # print extra arguments
    for key, value in extra.items():
        print 'extra key=%s value=%s' % (key,value)
    
    # populate input with search constraints from HTTP request
    input = SearchInput()
    for key in searchConfig.facetProfile.getKeys():
        if (request.REQUEST.get(key, None)):
            for value in request.REQUEST.getlist(key):
                if value:
                    input.addConstraint(key, value)
    
    # add fixed constraints - override previous values
    for key, values in searchConfig.fixedConstraints.items():
            input.setConstraint(key, values)
    
    # text
    if request.REQUEST.get('text', None):
        input.text = request.REQUEST['text']
    # type
    if request.REQUEST.get('type', None):
        input.type = request.REQUEST['type']
    # offset, limit
    if request.REQUEST.get('offset', 0):
        input.offset = int(request.REQUEST['offset'])
    if request.REQUEST.get('limit', 0):
        input.limit = int(request.REQUEST['limit'])
        
    # GET/POST switch
    print "HTTP Request method=%s" % request.method
    if (request.method=='GET'):
        return search_get(request, input, searchConfig.facetProfile, searchConfig.searchService, extra)
    else:
        return search_post(request, input, searchConfig.facetProfile, searchConfig.searchService, extra)
        
def search_get(request, searchInput, facetProfile, searchService, extra={}):
    
    #data = {}
    # pass on all the extra arguments
    data = extra
    
    # after POST redirection
    if (request.GET.get(SEARCH_DATA)):
        print "Retrieving search data from session"
        data = request.session.get(SEARCH_DATA, None)
        if data.get(ERROR_MESSAGE,None):
            print "Found Error=%s" % data[ERROR_MESSAGE]
    
    # first GET invocation
    else:
        
        # set retrieval of all facets in profile
        searchInput.facets = facetProfile.getKeys()
        
        # execute query for facets
        #searchOutput = searchService.search(searchInput, False, True)
        try:
            xml = searchService.search(searchInput, False, True)
            searchOutput = deserialize(xml, facetProfile)
            #FIXME
            #searchOutput.printme()
            
            data[SEARCH_INPUT] = searchInput
            data[SEARCH_OUTPUT] = searchOutput
            data[FACET_PROFILE] = facetProfile.getKeys()
            data['title'] = 'Search'
            
            # save data in session
            request.session[SEARCH_DATA] = data
            
        except HTTPError:
            print "HTTP Request Error"
            data = request.session[SEARCH_DATA]
            data[SEARCH_INPUT] = searchInput
            data[ERROR_MESSAGE] = "Error: HTTP request resulted in error, search may not be properly configured "
        
    return render_to_response('cog/search/search.html', data, context_instance=RequestContext(request))    
    
    
def search_post(request, searchInput, facetProfile, searchService, extra={}):
    
    # valid user input
    if (searchInput.isValid()):
        
        # set retrieval of all facets in profile
        searchInput.facets = facetProfile.getKeys()
    
        # execute query for results, facets
        #searchOutput = searchService.search(searchInput, True, True)
        try:
            xml = searchService.search(searchInput, True, True)
            searchOutput = deserialize(xml, facetProfile)
            #searchOutput.printme()
            
            # initialize new session data from extra argument dictionary
            data = extra
            data[SEARCH_INPUT] = searchInput
            data[SEARCH_OUTPUT] = searchOutput
            data[FACET_PROFILE] = facetProfile.getKeys()  
            
        except HTTPError:
            print "HTTP Request Error"
            data = request.session[SEARCH_DATA]
            data[SEARCH_INPUT] = searchInput
            data[ERROR_MESSAGE] = "Error: HTTP request resulted in error, search may not be properly configured "

            
    # invalid user input
    else:
        print "Invalid Search Input"
        # re-use previous data (output, profile and any extra argument) from session
        data = request.session[SEARCH_DATA]
        # override search input from request
        data[SEARCH_INPUT] = searchInput
        # add error
        data[ERROR_MESSAGE] = "Error: search text cannot contain any of the characters: %s" % INVALID_CHARACTERS;
         
    # store data in session 
    data['title'] = 'Search'
    request.session[SEARCH_DATA] = data
    
    # use POST-REDIRECT-GET pattern with additional parameter "?search_data"
    #return HttpResponseRedirect( reverse('cog_search')+"?%s=True" % SEARCH_DATA )
    return HttpResponseRedirect( request.path+"?%s=True" % SEARCH_DATA )




# Note: all the facets available through the REST API are defined by the Search Services and returned by an unbound query
# Each client application (such as this controller) is responsible for using a sub-set of these facets, and providing appropriate labels
# (labels could be provided by the REST API, but there is no Solr schema for encoding the information)
"""
facetProfile = FacetProfile([ 
                             ('project','Data Project'),
                             ('model','Model'),
                             ('experiment','Experiment'),
                             ('cf_variable','CF Standard Name'), 
                             ('resolution','Resolution'), 
                             #'institute':'Institute', 
                              #'instrument':'Instrument', 
                              #'obs_project':'Mission', 
                              #'obs_structure':'Data Structure',
                              #'obs_type':'Measurement Type',
                              #'product':'Product', 
                              #'time_frequency':'Time Frequency',
                              #'realm':'Realm',  
                             ('variable','Variable'),
                           ])
"""


# method to configure the search on a per-request basis
def getSearchConfig(request, project):
    
    # configure project search profile, if not existing already
    try:
        profile = project.searchprofile
    except SearchProfile.DoesNotExist:
        profile = create_project_search_profile(project)
                        
    # configure URL of back-end search service
    searchService = SolrSearchService(profile.url, profile.facets())
    
    # configure facets
    facets = []
    for facet in project.searchprofile.facets():    
        facets.append((facet.key,facet.label))
    
    # configure fixed search constraints
    # fixedConstraints = { 'project': ['dycore_2009'], } 
    fixedConstraints = {}   
    if project.searchprofile.constraints:
        constraints = project.searchprofile.constraints.split(',')
        for constraint in constraints:
            (key,value) = constraint.strip().split('=')
            try:
                fixedConstraints[key].append(value)
            except KeyError:
                fixedConstraints[key] = [value]
            
    # How to use TestSerachService instead
    #searchService = TestSearchService()
    #facets = []
    #for key, facet in searchService.myfacets.items():
    #    facets.append((facet.key,facet.label))

    return SearchConfig(FacetProfile(facets), fixedConstraints, searchService)
                
def search(request, project_short_name):
    """
    COG-specific search-view that configures the back-end search engine on a per-project basis.
    """
    # retrieve project from database
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    config = getSearchConfig(request, project)

    if config:        
        config.printme()
        # pass on project as extra argument to search
        return search_config(request, config, extra = {'project' : project} )
    # search is not configured for this project
    else:
        messages = ['Searching is not enabled for this project.',
                    'Please contact the project administrators for further assistance.']
        return render_to_response('cog/common/message.html', {'project' : project, 'messages':messages }, context_instance=RequestContext(request))

def search_profile_config(request, project_short_name):
    
    # retrieve project from database
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # security check
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)

    if request.method=='GET':
        # retrieve project search profile
        try:
            profile = project.searchprofile
        # or create a new one
        except ObjectDoesNotExist:
            profile = create_project_search_profile(project)
            
        form = SearchProfileForm(instance=profile)
            
        return render_search_profile_form(request, project, form)
        
    else:
        
        # create form object from request parameters and existing search profile
        try:
            form = SearchProfileForm(request.POST, instance=project.searchprofile)
        # or create a new object
        except ObjectDoesNotExist:
            form = SearchProfileForm(request.POST)
        
        if form.is_valid():
            
            # save profile to the database
            profile = form.save()
            
            # redirect to project home (GET-POST-REDIRECT)
            return HttpResponseRedirect(reverse('project_home', args=[project.short_name.lower()]))
            
        else:
            print 'Form is invalid: %s' % form
            return render_search_profile_form(request, project, form)
            

    
# method to add a new facet
def search_facet_add(request, project_short_name):
    
    # retrieve project from database
    project = get_object_or_404(Project, short_name__iexact=project_short_name)
    
    # security check
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    if request.method=='GET': 
        # assign order to new facet
        order = len(project.searchprofile.facets())
        facet = SearchFacet(order=order)
        form = SearchFacetForm(instance=facet)    
        return render_search_facet_form(request, project, form)
        
    else:
        form = SearchFacetForm(request.POST)
        
        if form.is_valid():            
            facet = form.save()
            return HttpResponseRedirect(reverse('search_profile_config', args=[project.short_name.lower()])) 
        
        else:     
            print 'Form is invalid: %s' % form.errors
            return render_search_facet_form(request, project, form)
        
# method to update an existing facet
def search_facet_update(request, facet_id):
    
    # retrieve facet from database
    facet = get_object_or_404(SearchFacet, pk=facet_id)
       
    # security check
    project = facet.profile.project
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    if request.method=='GET':    
        form = SearchFacetForm(instance=facet)    
        return render_search_facet_form(request, project, form)
        
    else:
        
        form = SearchFacetForm(request.POST, instance=facet)
        
        if form.is_valid():            
            facet = form.save()
            return HttpResponseRedirect(reverse('search_profile_config', args=[project.short_name.lower()])) 
        
        else:     
            print 'Form is invalid: %s' % form.errors
            return render_search_facet_form(request, project, form)

def search_facet_delete(request, facet_id):
         
    # retrieve facet from database
    facet = get_object_or_404(SearchFacet, pk=facet_id)
    
    # retrieve associated project
    project = facet.profile.project
    
    # security check
    if not userHasAdminPermission(request.user, project):
        return HttpResponseForbidden(PERMISSION_DENIED_MESSAGE)
    
    # delete facet
    facet.delete()
    
    # re-order all profile facets
    count = 0
    for facet in project.searchprofile.facets():
        facet.order = count
        facet.save()
        count += 1
        
    # redirect to project home (GET-POST-REDIRECT)
    return HttpResponseRedirect(reverse('search_profile_config', args=[project.short_name.lower()]))

def search_files(request, dataset_id, index_node):
    """View that searches for all files of a given dataset, and returns the response as JSON"""
    
    params = [ ('type',"File"), ('dataset_id',dataset_id), ("format", "application/solr+json") ]
 
                
    url = "http://"+index_node+"/esg-search/search?"+urllib.urlencode(params)
    #print 'Solr search URL=%s' % url
    fh = urllib2.urlopen( url )
    response = fh.read().decode("UTF-8")
    # FIXME
    #print response
    return HttpResponse(response, mimetype="application/json")

            
def render_search_profile_form(request, project, form):
    return render_to_response('cog/search/search_profile_form.html', 
                              {'project' : project, 'form':form, 'title':'Project Search Configuration' }, 
                               context_instance=RequestContext(request))
    
def render_search_facet_form(request, project, form):
    return render_to_response('cog/search/search_facet_form.html', 
                              {'project' : project, 'form':form, 'title':'Search Facet Configuration' }, 
                              context_instance=RequestContext(request))