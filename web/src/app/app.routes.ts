import { Routes } from '@angular/router';
import { ArchivePage } from './archive/archive-page';
import { DocumentPage } from './intake/document-page';
import { IntakePage } from './intake/intake-page';
import { WorkOrderReviewPage, unsavedReviewChangesGuard } from './review/work-order-review-page';

export const routes: Routes = [
  { path: '', component: IntakePage, title: 'eLedgerCare – submit document' },
  { path: 'archive', component: ArchivePage, title: 'eLedgerCare – archive search' },
  { path: 'documents/:documentId', component: DocumentPage, title: 'eLedgerCare – document' },
  {
    path: 'documents/:documentId/review',
    component: WorkOrderReviewPage,
    canDeactivate: [unsavedReviewChangesGuard],
    runGuardsAndResolvers: 'paramsOrQueryParamsChange',
    title: 'eLedgerCare – work-order review',
  },
  {
    path: 'documents/:documentId/review/revisions/:revisionNumber',
    component: WorkOrderReviewPage,
    canDeactivate: [unsavedReviewChangesGuard],
    runGuardsAndResolvers: 'paramsOrQueryParamsChange',
    title: 'eLedgerCare – work-order review revision',
  },
  { path: '**', redirectTo: '' },
];
