from celery import shared_task
from django.contrib import admin
from sklearn.cross_validation import train_test_split
from sklearn.datasets import load_digits
from tpot import TPOTClassifier

from training_server.celery import app
from training_server.models import AutoSklearnConfig

from automl_systems.auto_sklearn.run import train as train_auto_sklearn
from automl_systems.tpot.run import train_tpot


import autosklearn.classification
import sklearn.model_selection
import sklearn.datasets
import sklearn.metrics

@shared_task
def train():
    X, y = sklearn.datasets.load_digits(return_X_y=True)
    print('About to go down!')
    X_train, X_test, y_train, y_test = \
        sklearn.model_selection.train_test_split(X, y, random_state=1)
    automl = autosklearn.classification.AutoSklearnClassifier(time_left_for_this_task=300, per_run_time_limit=30, ml_memory_limit=8192)
    automl.fit(X_train, y_train)
    y_hat = automl.predict(X_test)
    print("Accuracy score", sklearn.metrics.accuracy_score(y_test, y_hat))


class AutoSklearnConfigAdmin(admin.ModelAdmin):
    list_display = ('status', 'date_trained', 'model_path', 'additional_remarks')

    fieldsets = (
        ('General Info:', {'fields':('framework', 'status', 'date_trained', 'model_path', 'logging_config', 'additional_remarks')}),
        ('Resource Options:', {'fields': ('run_time', 'per_instance_runtime', 'memory_limit')}),
        ('Model Training Options:', {'fields': ('initial_configurations_via_metalearning', 'ensemble_size', 'ensemble_nbest', 'seed', 'include_estimators', 'exclude_estimators', 'include_preprocessors', 'exclude_preprocessors', 'resampling_strategy', 'shared_mode')}),
        ('Caching and storage:', {'fields': ('output_folder', 'delete_output_folder_after_terminate', 'tmp_folder', 'delete_tmp_folder_after_terminate', 'additional_remarks')})
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ['status', 'model_path', 'date_trained', 'logging_config', 'additional_remarks']
        if obj:
            if not 'framework' in readonly_fields:
                readonly_fields.append('framework')
            if obj.training_triggered:
                return [f.name for f in self.model._meta.fields]
        return readonly_fields


    def save_model(self, request, obj, form, change):
        obj.training_triggered = True
        obj.status = 'waiting'
        obj.save()
        #train_auto_sklearn.s(obj.id).apply_async()
        train_auto_sklearn(obj.id)
        super(AutoSklearnConfigAdmin, self).save_model(request, obj, form, change)

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(AutoSklearnConfig, AutoSklearnConfigAdmin)
