import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import ReconciliationService
from .serializers import DisagreementSerializer, SummaryMetricsSerializer
from .models import Location

logger = logging.getLogger(__name__)

VALID_REASONS = {
    'MISSING_IN_B',
    'ORPHAN_IN_B',
    'DUPLICATE_IN_B',
    'VALUE_MISMATCH',
    'LOCATION_MISMATCH',
    'DATE_MISMATCH',
}

VALID_SORT_FIELDS = {
    'value',
    '-value',
    'record_id',
    '-record_id',
    'reason',
    '-reason',
}


class DisagreementListView(APIView):
    """
    GET /api/disagreements/
    
    Query parameters:
    - org: mandatory (e.g. 'ORG-A', 'ORG-B')
    - reason: optional (e.g. 'VALUE_MISMATCH', 'MISSING_IN_B', etc.)
    - sort: optional ('value', '-value', 'record_id', '-record_id', 'reason', '-reason')
    """
    def get(self, request):
        org = request.query_params.get('org')
        if not org or not org.strip():
            return Response(
                {"error": "Organization parameter 'org' is mandatory. Example: ?org=ORG-A"},
                status=status.HTTP_400_BAD_REQUEST
            )
        org = org.strip()

        # Validate organization
        available_orgs = sorted(list(Location.objects.values_list('org_id', flat=True).distinct()))
        if org not in available_orgs:
            return Response(
                {
                    "error": f"Invalid organization '{org}'. Available organizations: {available_orgs}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate reason if supplied
        reason = request.query_params.get('reason')
        if reason:
            reason = reason.strip().upper()
            if reason != 'ALL' and reason not in VALID_REASONS:
                return Response(
                    {
                        "error": f"Invalid reason '{reason}'. Valid reasons: {sorted(list(VALID_REASONS))}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if reason == 'ALL':
                reason = None

        # Validate sort if supplied
        sort_by = request.query_params.get('sort')
        if sort_by:
            sort_by = sort_by.strip()
            if sort_by not in VALID_SORT_FIELDS:
                return Response(
                    {
                        "error": f"Invalid sort parameter '{sort_by}'. Valid options: {sorted(list(VALID_SORT_FIELDS))}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            results = ReconciliationService.get_disagreements_for_tenant(
                org_id=org,
                reason=reason,
                sort_by=sort_by
            )
            serializer = DisagreementSerializer(results, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Error executing reconciliation query")
            return Response(
                {"error": "An internal error occurred while processing the reconciliation request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SummaryMetricsView(APIView):
    """
    GET /api/summary/
    Query parameters:
    - org: mandatory (e.g. 'ORG-A')
    """
    def get(self, request):
        org = request.query_params.get('org')
        if not org or not org.strip():
            return Response(
                {"error": "Organization parameter 'org' is mandatory. Example: ?org=ORG-A"},
                status=status.HTTP_400_BAD_REQUEST
            )
        org = org.strip()
        available_orgs = sorted(list(Location.objects.values_list('org_id', flat=True).distinct()))
        if org not in available_orgs:
            return Response(
                {"error": f"Invalid organization '{org}'. Available organizations: {available_orgs}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            metrics = ReconciliationService.get_summary_metrics(org_id=org)
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Error computing summary metrics")
            return Response(
                {"error": "An internal error occurred while computing summary metrics."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrganizationListView(APIView):
    """
    GET /api/organizations/
    Returns list of authoritative organizations from locations.
    """
    def get(self, request):
        orgs = sorted(list(Location.objects.values_list('org_id', flat=True).distinct()))
        return Response({"organizations": orgs}, status=status.HTTP_200_OK)
