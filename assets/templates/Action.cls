global with sharing class <ACTION> {
    global class Request { @InvocableVariable global String recordId; }

    // Single-field wrapper -- the field name <ANCHOR> is the binding anchor.
    // A FLAT List<<PAYLOAD>> return breaks the binding path (see binding-anchor.md).
    global class Response { @InvocableVariable global <PAYLOAD> <ANCHOR>; }

    global class <PAYLOAD> {
        @InvocableVariable global String title;
        @InvocableVariable global List<Row> rows;   // list attrs are fine
    }
    global class Row {
        @InvocableVariable global String name;
        @InvocableVariable global Decimal amount;
    }

    @InvocableMethod(label='<LABEL>' description='<LABEL>')
    global static List<Response> run(List<Request> requests) {
        Response res = new Response();
        res.<ANCHOR> = build(requests);   // build your <PAYLOAD>
        return new List<Response>{ res };
    }

    private static <PAYLOAD> build(List<Request> requests) {
        // TODO: SOQL against standard objects, as the signed-in user.
        <PAYLOAD> p = new <PAYLOAD>();
        p.title = 'TODO';
        p.rows = new List<Row>();
        return p;
    }
}
