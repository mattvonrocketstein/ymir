#
# service/puppet/install_service.pp
#
# Bootstraps very basic stuff for this service.
#

# set the standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

# system packages
package { 'nmap': ensure => present }
package {'tree': ensure=> present }
package {'ack-grep': ensure=> present }
package {'python-dev': ensure=> present }
package {'python-virtualenv': ensure=> present }

# example that creates a common directory for logs
#file {'/opt/my_service/':
#  ensure  => directory,
#  recurse => true,
#}
#file {'/opt/my_service/logs':
#  ensure  => directory,
#  recurse => true,
#  require => File['/opt/my_service']
#}
#exec{ 'writable-logdir':
#  command => 'chmod uog+rwx /opt/my_service/logs',
#  require => File['/opt/my_service/logs']
#}
