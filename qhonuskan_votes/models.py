from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.dispatch import Signal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from django.conf import settings
try:
    from django.contrib.auth import get_user_model
    User = settings.AUTH_USER_MODEL
except ImportError:
    from django.contrib.auth.models import User

vote_changed = Signal(providing_args=["voter", "object"])

_vote_models = {}

# Managers --------------------------------------------------------------------


class ObjectsWithScoresManager(models.Manager):
    """
    Returns objects with their scores
    """
    def get_queryset(self):
        return super(ObjectsWithScoresManager, self).get_queryset().annotate(
            vote_score=Coalesce(Sum('%svote__value' % self.model._meta.model_name), 0)
        )


class SortByScoresManager(models.Manager):
    """
    Returns objects with their scores and orders them by value (1,0,-1)
    """
    def get_queryset(self):
        return super(SortByScoresManager, self).get_queryset().annotate(
            vote_score=Coalesce(Sum('%svote__value' % self.model._meta.model_name, 0)
            )
        ).order_by('-vote_score')


# Fields ----------------------------------------------------------------------


class VotesField(object):
    """
    Usage:

    class MyModel(models.Model):
        ...
        Votes = VotesField()
    """
    def __init__(self):
        pass

    def contribute_to_class(self, cls, name):
        self._name = name

        descriptor = self._create_Vote_model(cls)
        setattr(cls, self._name, descriptor)

    def _create_Vote_model(self, model):
        class VoteMeta(ModelBase):
            """
            Make every Vote model have their own name/table.
            """
            def __new__(c, name, bases, attrs):

                # Rename class
                name = '%sVote' % model._meta.object_name

                # This attribute is required for a model to function
                # properly in Django.
                attrs['__module__'] = model.__module__

                vote_model = ModelBase.__new__(c, name, bases, attrs)

                _vote_models[vote_model.get_model_name()] = vote_model

                return vote_model

        rel_nm_user = '%s_votes' % model._meta.object_name.lower()

        class Vote(models.Model):
            """
            Vote model
            """
            __metaclass__ = VoteMeta

            voter = models.ForeignKey(
                User,
                verbose_name=_('voter'))

            value = models.IntegerField(
                default=1,
                verbose_name=_('value'))

            date = models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                verbose_name=_('voted on'))

            object = models.ForeignKey(
                model,
                verbose_name=_('object'))

            class Meta:
                ordering = ('date',)
                verbose_name = _('Vote')
                verbose_name_plural = _('Votes')
                unique_together = ('voter', 'object')

            def save(self, *args, **kwargs):

                if self.pk is not None:
                    orig_vote = Vote.objects.get(pk=self.pk)
                    if orig_vote.value != self.value:
                        vote_changed.send(sender=self)
                else:
                    vote_changed.send(sender=self)
                super(Vote, self).save(*args, **kwargs)

            def delete(self, *args, **kwargs):
                super(Vote, self).delete(*args, **kwargs)
                vote_changed.send(sender=self)

            def __unicode__(self):
                values = {
                    'voter': self.voter.username,
                    'like': _('likes') if self.value > 0 else _('hates'),
                    'object': self.object}

                return "%(voter)s %(like)s %(object)s" % values

            @classmethod
            def get_model_name(self):
                return '%s.%s' % (self._meta.app_label, self._meta.object_name)

        class VoteFieldDescriptor(object):
            def __init__(self):
                pass

            def __get__(self, obj, objtype):
                """
                Return the related manager for the Votes.
                """
                if obj:
                    return getattr(obj,
                        ('%svote_set' % model._meta.object_name).lower())
                else:
                    return Vote.objects

        return VoteFieldDescriptor()
