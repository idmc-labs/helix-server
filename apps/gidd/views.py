from datetime import datetime
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.writer.excel import save_virtual_workbook

from apps.country.models import Country
from .models import (
    Conflict, Disaster, DisplacementData, IdpsSaddEstimate,
    StatusLog,
)
from .serializers import (
    CountrySerializer,
    ConflictSerializer,
    DisasterSerializer,
    DisplacementDataSerializer,
)
from .rest_filters import (
    RestConflictFilterSet,
    RestDisasterFilterSet,
    RestDisplacementDataFilterSet,
    IdpsSaddEstimateFilter,
)
from utils.common import track_gidd
from apps.entry.models import ExternalApiDump


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()
    lookup_field = 'iso3'
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['id']


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConflictSerializer
    queryset = Conflict.objects.all().select_related('country')
    filterset_class = RestConflictFilterSet


class DisasterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisasterSerializer
    queryset = Disaster.objects.all().select_related('country')
    filterset_class = RestDisasterFilterSet

    @action(
        detail=False,
        methods=["get"],
        url_path="disaster-export",
        permission_classes=[AllowAny],
    )
    def export(self, request):
        """
        Export disaster
        """

        qs = self.filter_queryset(self.get_queryset())
        track_gidd(
            request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_DISASTER_EXPORT_REST
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "1_Displacement data"
        ws.append([
            'ISO3', 'Country / Territory', 'Year', 'Event Name', 'Date of Event (start)',
            'Disaster Internal Displacements', 'Hazard Category', 'Hazard Type', 'Hazard Sub Type'
        ])
        for disaster in qs:
            ws.append(
                [
                    disaster.country.iso3,
                    disaster.country.name,
                    disaster.year,
                    disaster.event_name,
                    disaster.start_date,
                    disaster.new_displacement_rounded,
                    disaster.hazard_category_name,
                    disaster.hazard_type_name,
                    disaster.hazard_sub_type_name,
                ]
            )
        ws2 = wb.create_sheet('README')
        readme_text = [
            ['Title', 'Global Internal Displacement Database (GIDD)'],
            ['File name', 'IDMC_GIDD_disasters_internal_displacement_data'],
            ['Creator', 'Internal Displacement monitoring Centre (IDMC)'],
            ['Date extracted', datetime.now().strftime("%d/%m/%Y")],
            ['Last update', StatusLog.last_release_date()],
            [],
            [
                'Description',
                'The data includes figures on internal displacement in different countries and regions from '
                '2009 to 2022 for conflict induced displacement and from 2008 to 2022 for disaster induced displacement.'
            ],
            [
                'The main definitions used are described below, for further information and more robust descriptions '
                'of definitions please refer to https	//www.internal-displacement.org/monitoring-tools'
            ],
            [
                '− Internal displacements correspond to the estimated number of internal displacements over a given '
                'period of time (reporting year). Figures may include individuals who have been displaced more than once.'
            ],
            [
                '− Total number of IDPs: Represents the total number of Internal displaced Person “IDPs”, in a given '
                'location at a specific point in time. It could be understood as the total number of people living in a '
                'situation of displacement as of the end of the reporting year.'
            ],
            [
                '− Event name', 'Disaster events can be triggered by natural hazards such as weather or geophysical '
                'phenomena. When a disaster event has an internationally recognized name, IDMC adopts that name. '
                'Otherwise, the event is coded based on the country, type of hazard, location, and start date of the event.'
            ],
            [
                'Use license: Content is licensed under CC BY-NC (See: '
                'https://creativecommons.org/licenses/by/4.0/)'
            ],
            ['Coverage:', 'Worldwide'],
            ['Contact:', 'ch-idmcdataandanalysishub@idmc.ch'],
        ]

        for item in readme_text:
            ws2.append(item)
        ws2.append([])
        ws2.append(['Table description:'])
        ws2.append([])

        table = [
            ['ISO3: ISO 3166-1 alpha-3. The ISO3 "AB9" was assigned to the Abyei Area'],
            ['Country / Territory: Country’s or territory short name'],
            ['Year: Year of the event figures'],
            [
                'Event Name:  IDMC adopts that name. Otherwise, the event is coded based '
                'on the country, type of hazard, location, and start date of the event.'
            ],
            ['Date of event (start): Approximate starting date of the event'],
            [
                'Disaster Internal Displacements: Total number of internal displacements '
                'reported (rounded figures at national level), as a result of disasters over the reporting year.'
            ],
            ['Hazard Category: Hazard category based on CRED EM-DAT.'],
            ['Hazard Type: Hazard type category based on CRED EM-DAT.'],
            ['Hazard Sub Type: Hazard sub-type category based on CRED EM-DAT.'],
        ]
        for item in table:
            ws2.append(item)
        response = HttpResponse(content=save_virtual_workbook(wb))
        filename = 'IDMC_GIDD_Disasters_Internal_Displacement_Data.xlsx'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


class DisplacementDataViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisplacementDataSerializer
    queryset = DisplacementData.objects.all()
    filterset_class = RestDisplacementDataFilterSet

    def export_conflicts(self, ws, qs):
        track_gidd(
            self.request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_DISASTER_EXPORT_REST
        )
        ws.append([
            'ISO3',
            'Name',
            'Year',
            'Conflict Stock Displacement',
            'Conflict Stock Displacement (Raw)',
            'Conflict Internal Displacements',
            'Conflict Internal Displacements (Raw)',
        ])
        for item in qs:
            ws.append([
                item.iso3,
                item.country_name,
                item.year,
                item.conflict_total_displacement_rounded,
                item.conflict_total_displacement,
                item.conflict_new_displacement_rounded,
                item.conflict_new_displacement,
            ])

    def export_disasters(self, ws, qs):
        track_gidd(
            self.request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_DISPLACEMENT_EXPORT_REST
        )
        ws.append([
            'ISO3',
            'Name',
            'Year',
            'Disaster Internal Displacements',
            'Disaster Internal Displacements (Raw)',
            'Disaster Stock Displacement',
            'Disaster Stock Displacement (Raw)'
        ])
        for item in qs:
            ws.append([
                item.iso3,
                item.country_name,
                item.year,
                item.disaster_new_displacement_rounded,
                item.disaster_new_displacement,
                item.disaster_total_displacement_rounded,
                item.disaster_total_displacement,
            ])

    def export_displacements(self, ws, qs):
        track_gidd(
            self.request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_DISPLACEMENT_EXPORT_REST
        )
        ws.append([
            'ISO3',
            'Name',
            'Year',
            'Conflict Stock Displacement',
            'Conflict Stock Displacement (Raw)',
            'Conflict Internal Displacements',
            'Conflict Internal Displacements (Raw)',
            'Disaster Internal Displacements',
            'Disaster Internal Displacements (Raw)',
            'Disaster Stock Displacement',
            'Disaster Stock Displacement (Raw)'
        ])
        for item in qs:
            ws.append([
                item.iso3,
                item.country_name,
                item.year,
                item.conflict_total_displacement_rounded,
                item.conflict_total_displacement,
                item.conflict_new_displacement_rounded,
                item.conflict_new_displacement,
                item.disaster_new_displacement_rounded,
                item.disaster_new_displacement,
                item.disaster_total_displacement_rounded,
                item.disaster_total_displacement,
            ])

    @action(
        detail=False,
        methods=["get"],
        url_path="displacement-export",
        permission_classes=[AllowAny],
    )
    def export(self, request):
        """
        Export displacements, conflict and disaster
        """

        # Track export
        qs = self.filter_queryset(self.get_queryset()).order_by(
            '-year',
            'iso3',
        )

        wb = Workbook()
        ws = wb.active
        # Tab 1
        ws.title = "1_Displacement data"
        if request.GET.get('cause') == 'conflict':
            self.export_conflicts(ws, qs)
        elif request.GET.get('cause') == 'disaster':
            self.export_disasters(ws, qs)
        else:
            self.export_displacements(ws, qs)
        # Tab 2
        ws2 = wb.create_sheet('IDPS_SADD_estimates')
        ws2.append([
            'ISO3',
            'Country',
            'Year',
            'Sex',
            'Cause',
            '0-1',
            '0-4',
            '0-14',
            '0-17',
            '0-24',
            '5-11',
            '5-14',
            '12-14',
            '12-16',
            '15-17',
            '15-24',
            '25-64',
            '65+',
        ])
        idps_sadd_qs = IdpsSaddEstimateFilter(
            data=self.request.query_params, queryset=IdpsSaddEstimate.objects.all()
        ).qs
        for item in idps_sadd_qs:
            ws2.append([
                item.iso3,
                item.country_name,
                item.year,
                item.sex,
                item.cause.label,
                item.zero_to_one,
                item.zero_to_four,
                item.zero_to_forteen,
                item.zero_to_sventeen,
                item.zero_to_twenty_four,
                item.five_to_elaven,
                item.five_to_fourteen,
                item.twelve_to_fourteen,
                item.twelve_to_sixteen,
                item.fifteen_to_seventeen,
                item.fifteen_to_twentyfour,
                item.twenty_five_to_sixty_four,
                item.sixty_five_plus,
            ])
        # Tab 3
        ws3 = wb.create_sheet('README')
        readme_text = [
            ['Title: Global Internal Displacement Database (GIDD)'],
            ['File name: IDMC_Internal_Displacement_Conflict-Violence_Disasters'],
            ['Creator: Internal Displacement monitoring Centre (IDMC)'],

            ['Date extracted', datetime.now().strftime("%d/%m/%Y")],
            ['Last update', StatusLog.last_release_date()],
            [''],
            [
                'Description: The data includes figures on internal displacement '
                'in different countries and regions from 2009 to 2022 for conflict '
                'induced displacement and from 2008 to 2022 for disaster induced displacement.'
            ],
            [
                'The main definitions used are described below, for further information '
                'and more robust descriptions of definitions please refer to '
                'https://www.internal-displacement.org/monitoring-tools'
            ],
            [''],
            [
                '− Internal displacements correspond to the estimated number of internal '
                'displacements over a given period of time (reporting year). Figures may '
                'include individuals who have been displaced more than once.'
            ],
            [
                '− Total number of IDPs: Represents the total number of Internally Displaced '
                'Person “IDPs”, in a given location at a specific point in time. It could be '
                'understood as the total number of people living in a situation of '
                'displacement as of the end of the reporting year.'
            ],
            [''],
            [
                'Use license: Content is licensed under CC BY-NC (See: '
                'https://creativecommons.org/licenses/by-nc/4.0/)'
            ],

            ['Coverage: Worldwide'],
            ['Contact: ch-idmcdataandanalysishub@idmc.ch'],
            [''],
            [''],
            ['Methodological notes for the 2023 release:'],
            [
                '− The description of our methodology is available at '
                'https://www.internal-displacement.org/monitoring-tools'],
            [
                '− This is the first time IDMC reports on IDPs in Serbia since 2015, which '
                'is not due to internal displacements in 2022 but to a review of the context in '
                'which displacement occurred. This decision was made to acknowledge that '
                'these IDPs did not cross an international border at the time of their '
                'displacement and to harmonise IDMC’s IDP estimates with those of the '
                'Government of Serbia and the UN agencies.'
            ],
            [
                '− As part of a methodological revision, IDMC has decided not to publish '
                'IDP total figures and Internal displacements for the countries listed below. '
                'This decision is aimed at maintaining the accuracy and integrity of our '
                'data and ensuring that it meets the highest standards of quality.'
            ],
            [''],
        ]

        for item in readme_text:
            ws3.append(item)

        table = [
            ['Country', 'Year', 'Displacement category'],
            ['Togo', '2019', 'IDPs'],
            ['South Africa', '2019', 'IDPs'],
            ['Ghana', '2019', 'IDPs'],
            ['Malawi', '2019', 'IDPs'],
            ['Tunisia', '2019', 'IDPs'],
            ['Togo', '2019', 'Internal Displacements'],
            ['Madagascar', '2019', 'Internal Displacements'],
            ['Benin', '2019', 'Internal Displacements'],
            ['Malawi', '2019', 'Internal Displacements'],
            ['Tunisia', '2019', 'Internal Displacements'],
            ['South Africa', '2020', 'IDPs'],
            ['South Africa', '2020', 'Internal Displacements'],
        ]
        for item in table:
            ws3.append(item)

        ws3.append([])
        ws3.append([])

        ws3.append([
            '− As part of a methodological revision and our ongoing commitment to providing '
            'the most accurate and reliable information on internal displacement, IDMC is '
            'pleased to announce the publication of IDP total figures and Internal '
            'displacements for certain countries and years that were not previously available. '
            'These figures have been carefully reviewed and verified by our team of experts '
            'to ensure the highest standards of quality.'

        ])
        ws3.append([])

        table2 = [
            ['Country', 'Year', 'Displacement category'],
            ['Israel', '2016', 'Internal displacements'],
            ['Israel', '2017 ', 'Internal displacements'],
            ['Israel', '2018', 'Internal displacements'],
            ['Kyrgyzstan', '2019', 'IDPs'],
            ['Israel', '2019', 'Internal displacements'],
            ['Nicaragua', '2020', 'IDPs'],
            ['Nicaragua', '2020', 'Internal displacements'],
            ['Nicaragua', '2021', 'IDPs'],
        ]

        for item in table2:
            ws3.append(item)

        ws3.append([])
        ws3.append([
            '− As part of a methodological revision some figures published may differ from '
            'previous publications due to retroactive changes or the inclusion of previously '
            'unavailable data. We encourage our data users to refer to the latest version of '
            'our publications for the most up-to-date information.'
        ])
        ws3.append([])
        ws3.append(['1_ Displacement data (Tab table description):'])
        ws3.append([])
        readme_text_2 = [
            ['Where (raw) means “not rounded”.'],
            ['ISO3: ISO 3166-1 alpha-3. The ISO3 “AB9” was assigned to the Abyei Area'],
            ['Name: Country’s or territory short name '],
            ['Year: Year of the reporting figures'],
            [
                'Conflict Total number of IDPs: Total number of IDPs (rounded figures at '
                'national level), as a result, of Conflict and Violence as of the end of '
                'the reporting year.'
            ],
            [
                'Conflict Total number of IDPs raw: Total number of IDPs (not rounded), as '
                'a result, of Conflict and Violence as of the end of the reporting year.'
            ],
            [
                'Conflict Internal Displacements: Total number of internal displacements '
                'reported (rounded figures at national level), as a result of Conflict and '
                'Violence over the reporting year.'
            ],
            [
                'Conflict Internal Displacements raw: Total number of internal displacements '
                'reported (not rounded), as a result of Conflict and Violence over the '
                'reporting year.'
            ],
            [
                'Disaster Internal Displacements: Total number of internal displacements reported '
                '(rounded figures at national '
                'level), as a result of disasters over the reporting year.'
            ],
            [
                'Disaster Internal Displacements raw: Total number of internal displacements reported '
                '(not rounded), as a result of disasters over the reporting year.'
            ],
            [
                'Disaster Total number of IDPs: Total number of IDPs (rounded figures at '
                'national level), as a result, of disasters as of the end of the reporting year.'
            ],
            [
                'Disaster Total number of IDPs raw: Total number of IDPs (not rounded), as a result, of disasters as of '
                'the end of the reporting year.'
            ],
        ]
        ws3.append([])
        for item in readme_text_2:
            ws3.append(item)
        ws3.append([])

        readme_text3 = [
            ['ISO3: ISO 3166-1 alpha-3. The ISO3 “AB9” was assigned to the Abyei Area'],
            ['Country: Country’s or territory short name'],
            ['Year: Reporting year of the data'],
            ['Sex: Data encoded into male, female and both sexes'],
            ['Cause: Cause of displacement'],
            [
                'Age groups are organized as follows: 0-1, 0-4, 0-14, 0-17, 0-24, 5-11, 5-14, '
                '12-14, 12-16, 15-17, 15-24, 25-64, 65+'
            ],
        ]
        ws3.append([])
        ws3.append([
            '2_IDPS_SADD_estimates (Tab table description):'
        ])
        ws3.append([])
        for item in readme_text3:
            ws3.append(item)
        ws3.append([])

        ws3.append([])
        ws3.append([
            'Disaggregating IDMC’s IDP Figures by Sex and Age methodological notes:'
        ])
        ws3.append([])
        ws3.append([
            'Sex and Age Disaggregated Data (SADD) for displacement associated with conflict or '
            'disasters is often scarce. One way to estimate it is to use SADD available at the national '
            'level. IDMC employs United Nations Population Estimates and Projections to break down the '
            'number of internally displaced people by sex and age. The methodology and limitations of '
            'this approach are described on IDMC’s website at: https://www.internal-displacement.org/monitoring-tools',
        ])

        response = HttpResponse(content=save_virtual_workbook(wb))
        filename = 'IDMC_Internal_Displacement_Conflict-Violence_Disasters.xlsx'
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response
