
def convPbToOp(pb):
    return pb
#    pbop = common_pb2.ProtocolWaveletOperation()
#    pbop.ParseFromString(pb)
#
#    print "ProtocolWaveletOperation contains this operation(s):"
#    for desc, val in pbop.ListFields():
#        print desc.name, val
#
#    if b

def convOpToPb(body):

    return body

#    pbop = common_pb2.ProtocolWaveletOperation()
#    
#    if body['type'] == 'WAVELET_ADD_PARTICIPANT':
#        participant = body['property']
#        pbop.add_participant = participant
#
#    elif body['type'] == 'OPERATION_MESSAGE_BUNDLE':
#        operations = body['property']['operations']
#        for op in operations:
#            if op['type'] == 'DOCUMENT_INSERT':
#                #XXX: i think, the blibId is the document id...
#                pbop.mutate_document.document_id = op['blipId']
#                #pbop.mutate_document.document_operation 
                    
#{"type":"DOCUMENT_INSERT","waveId":"CH0H59rYDc","waveletId":"CH0H59rYDc!conv+root","blipId":"X73f7P7ngh","index":31,"property":"s"} 
#    return pbop.SerializeToString()
