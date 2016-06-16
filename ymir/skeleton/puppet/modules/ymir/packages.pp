#
# puppet/modules/ymir/packages.pp
#
#   ymir's (opinionated) list of random system
#   packages which can be useful for devops
#
package { 'nmap': ensure => present }
package { 'nethogs': ensure => present }
package { 'htop': ensure => present }
package { 'mosh': ensure => present }
package { 'tree': ensure=> present }
package { 'ack-grep': ensure=> present }
package { 'mosh': ensure=> present }
package { 'python-dev': ensure=> present }
package { 'python-virtualenv': ensure=> present }
package { ['ruby-dev', 'gem']: ensure => present }
