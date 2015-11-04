#
# puppet/modules/ymir/ec2_facts.pp
#
#

# standard exec path
Exec { path => [ '/bin/', '/sbin/' , '/usr/bin/', '/usr/sbin/' ] }

file {'/etc/facter/':
  ensure  => directory,
  recurse => true,
}
file {'/etc/facter/facts.d':
  ensure  => directory,
  recurse => true,
  require => File['/etc/facter']
}->
file { '/etc/facter/facts.d/ec2_facts.py' :
    owner   => 'root',
    group   => 'root',
    mode    => '0777',
    content => template('ymir/ec2_facts.py')
}
