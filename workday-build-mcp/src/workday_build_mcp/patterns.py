"""Curated pattern catalog: pattern name -> canonical reference file(s).

Derived from the reference sample apps and the workday-extend-reference-lookup
skill. `find_pattern` uses this first, then falls back to graph search.
"""
from __future__ import annotations

PATTERNS: dict[str, list[str]] = {
    # PMD widgets / layouts
    "editable grid": ["pmdWidgetDictionary/presentation/gridsEdit.pmd"],
    "sortable filterable grid": ["pmdWidgetDictionary/presentation/sortFilterEditGrid.pmd"],
    "grid": ["pmdWidgetDictionary/presentation/grids.pmd", "pmdWidgetDictionary/presentation/gridsEdit.pmd"],
    "tabs": ["pmdWidgetDictionary/presentation/tabs.pmd"],
    "sidebar": ["pmdWidgetDictionary/presentation/sidebar.pmd"],
    "popup": ["pmdWidgetDictionary/presentation/popup.pmd"],
    "modal": ["pmdWidgetDictionary/presentation/popup.pmd"],
    "loops": ["pmdWidgetDictionary/presentation/loops.pmd"],
    "micro page": ["pmdWidgetDictionary/presentation/micro.pmd", "pmdWidgetDictionary/presentation/microConclusion.pmd"],
    "confirmation page": ["pmdWidgetDictionary/presentation/microConclusion.pmd"],
    "file upload": ["pmdWidgetDictionary/presentation/fileUploaderRow.pmd"],
    "cards": ["pmdWidgetDictionary/presentation/home.pmd"],
    "card container": ["pmdWidgetDictionary/presentation/home.pmd"],
    "chart": ["pmdWidgetDictionary/presentation/projectPlanning.pmd", "pmdWidgetDictionary/presentation/projectStatus.pmd"],
    # scripting
    "page events": ["pmdScripting/presentation/pageEvents.pmd", "pmdScripting/presentation/scripts/pageEvents.script"],
    "onload": ["pmdScripting/presentation/pageEvents.pmd", "pmdScripting/presentation/scripts/pageEvents.script"],
    "grid events": ["pmdScripting/presentation/gridEvents.pmd", "pmdScripting/presentation/scripts/gridEvents.script"],
    "date calculations": ["pmdScripting/presentation/dateCalculations.pmd", "pmdScripting/presentation/scripts/dateCalculations.script"],
    "invoke endpoint": ["pmdScripting/presentation/invokingEndpoints.pmd", "pmdScripting/presentation/scripts/invokingEndpoints.script"],
    "invoking endpoints": ["pmdScripting/presentation/invokingEndpoints.pmd", "pmdScripting/presentation/scripts/invokingEndpoints.script"],
    "logging": ["pmdScripting/presentation/logging.pmd", "pmdScripting/presentation/scripts/logging.script"],
    "update widget state": ["pmdScripting/presentation/updateWidgetState.pmd", "pmdScripting/presentation/scripts/updateWidgetState.script"],
    "data manipulation": ["pmdScripting/presentation/dataManipulation.pmd", "pmdScripting/presentation/scripts/dataManipulation.script"],
    # model
    "business object": ["agentapp_mqwqvh /model", "charitableDonationsWithSentimentAnalysis/model"],
    "report": ["charitableDonationsWithSentimentAnalysis/model/AllCharities.report"],
    "task": ["agentapp_mqwqvh /model"],
    "attachment": ["charitableDonationsWithSentimentAnalysis/model/CharityLogo.attachment"],
    "business process": ["charitableDonationsWithSentimentAnalysis/model/CreateCharity.businessprocess"],
    # full pages
    "hub page": ["charitableDonationsWithSentimentAnalysis/presentation/charityHub.pmd"],
    "list detail": ["charitableDonationsWithSentimentAnalysis/presentation/charitiesListDetail.pmd"],
    "wizard": ["charitableDonationsWithSentimentAnalysis/presentation/createCharityWizard.pmd"],
    # orchestrations
    "suborchestration error handling": ["orchestrateStarterKit/orchestration/OSK141_EH_API_Full.suborchestration"],
    "error handling": ["orchestrateStarterKit/orchestration/OSK141_EH_API_Full.suborchestration"],
    "soap": ["orchestrateStarterKit/orchestration/OSK103_SOAP_Read_WorkdayApiService.suborchestration"],
    "document storage": ["orchestrateStarterKit/orchestration/OSK106_StoreFile_Full_DocumentsService.suborchestration"],
    "event logging": ["orchestrateStarterKit/orchestration"],
    "settings management": ["orchestrateStarterKit/orchestration"],
    # agents
    "agent": ["jheadgrouptest_svfbfp/agents"],
    "agent skill": ["jheadgrouptest_svfbfp/agents"],
    "a2ui": ["jheadgrouptest_svfbfp/presentation"],
}
