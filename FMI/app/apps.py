﻿import django.apps
import seeker


class AppConfig (django.apps.AppConfig):
    name = 'app'

    def ready(self):
        import seeker
        import app.models as models

        #models.PostDoc = seeker.mapping.document_from_model(models.Post, index="post", using=models.client)
        es_index = {'document' : 'post', 'index' : 'post', 'doc_type' : 'doc', 'properties' : models.PostMap._meta.es_mapping}
        models.PostDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.PostSeekerView.document = models.PostDoc
        models.PostSeekerView.es_mapping = models.PostMap._meta.es_mapping

        #models.PerfumeDoc = seeker.mapping.document_from_model(models.Perfume, index="review", using=models.client)
        es_index = {'document' : 'perfume', 'index' : 'review', 'doc_type' : 'doc', 'properties' : models.Review._meta.es_mapping}
        models.PerfumeDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.PerfumeSeekerView.document = models.PerfumeDoc
        models.PerfumeSeekerView.es_mapping = models.Review._meta.es_mapping

        #models.PageDoc = seeker.mapping.document_from_model(models.Page, index="page", using=models.client)
        es_index = {'document' : 'page', 'index' : 'page', 'doc_type' : 'doc', 'properties' : models.PageMap._meta.es_mapping}
        models.PageDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.PageSeekerView.document = models.PageDoc
        models.PageSeekerView.es_mapping = models.PageMap._meta.es_mapping

        #models.FeedlyDoc = seeker.mapping.document_from_model(models.Feedly, index="feedly", using=models.client)
        es_index = {'document' : 'feedly', 'index' : 'feedly', 'doc_type' : 'doc', 'properties' : models.FeedlyMap._meta.es_mapping}
        models.FeedlyDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.FeedlySeekerView.document = models.FeedlyDoc
        models.FeedlySeekerView.es_mapping = models.FeedlyMap._meta.es_mapping

        #models.MailDoc = seeker.mapping.document_from_model(models.Mail, index="mail", using=models.client)
        es_index = {'document' : 'mail', 'index' : 'mail', 'doc_type' : 'doc', 'properties' : models.MailMap._meta.es_mapping}
        models.MailDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.MailSeekerView.document = models.MailDoc
        models.MailSeekerView.es_mapping = models.MailMap._meta.es_mapping

        #models.bestmatchDoc = seeker.mapping.document_from_model(models.bestmatch, index="bestmatch", using=models.client)
        es_index = {'document' : 'bestmatch', 'index' : 'bestmatch', 'doc_type' : 'doc', 'properties' : models.bestmatchMap._meta.es_mapping}
        models.bestmatchDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.bestmatchSeekerView.document = models.bestmatchDoc
        models.bestmatchSeekerView.es_mapping = models.bestmatchMap._meta.es_mapping

        #models.SurveyDoc = seeker.mapping.document_from_model(models.Survey, index="survey", using=models.client)
        es_index = {'document' : 'survey', 'index' : 'survey', 'doc_type' : 'doc', 'properties' : models.SurveyMap._meta.es_mapping}
        models.SurveyDoc = seeker.mapping.document_from_index(es_index, using=models.client)
        models.SurveySeekerView.document = models.SurveyDoc
        models.SurveySeekerView.es_mapping = models.SurveyMap._meta.es_mapping


