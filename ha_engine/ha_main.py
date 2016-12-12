from optparse import OptionParser
from ha_engine.ha_parser import HAParser
from ha_engine.ha_executor import HAExecutor
import ha_engine.ha_infra as common


LOG = common.ha_logging(__name__)  

def main(config_file, run_disruptors): 
    parser = HAParser(config_file, run_disruptors)
    executor = HAExecutor(parser)
    executor.run() 
    
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="config_file", 
                      action="store", type="string")
    parser.add_option("-k", "--run-disruptors", dest="run_disruptors", 
                      action="store_true", type="boolean", default=False)
    (options, args) = parser.parse_args()
    config_file = options.config_file 
    run_disruptors = options.run_disruptors
    main(config_file, run_disruptors) 

