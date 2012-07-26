from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
                       
    # welcome page              
    #url(r'^$', django.views.generic.base.TemplateViewas_view(template_name='cog/index.html')),
             
    # move notice
    # top-level old COG URL
    url(r'^thesitehasmoved/$', 'cog.views.thesitehasmoved', name='thesitehasmoved'),
    # old project sites
    url(r'^thesitehasmoved/(?P<project_short_name>.+)/$', 'cog.views.thisprojecthasmoved', name='thisprojecthasmoved'),
             
    # top-level old COG URL
    url(r'^cog/$', 'cog.views.earthsystemcog', name='earthsystemcog'),
        
    # old COG project URL
    url(r'^cog/(?P<project_short_name>.+)/$', 'cog.views.earthsystemcog_project', name='earthsystemcog_project'),
    
    # site index
    url(r'^$', 'cog.views.index', name='site_index'),
                       
    # Filebrowser Admin pages
    (r'^filebrowser/', include('filebrowser.urls')),

    # Administrator application
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
        
    # Comments
    (r'^comments/', include('django.contrib.comments.urls')),

    # TinyMCE
    (r'^tinymce/', include('tinymce.urls')),
    
    # media
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT} ),
    
    # POSTS application
    #(r'^posts/', include('posts.urls')),
    
    # MYAPP application
    #(r'^myapp/', include('myapp.urls')),
    

    # REMAPPING application
    #(r'^remap/', include('remap.urls')),
    
    # SEARCH application
    # Note: the actual search URLs used by COG are redefined in cog.urls
    #(r'^search/', include('search.urls')),
    
    # COG application
    (r'', include('cog.urls')),
    
    # cim-forms
    (r'^metadata/', include('django_cim_forms.urls')),
    (r'', include('dycore.urls')),

)