import com.hazelcast.collection.IQueue;
import com.hazelcast.core.Hazelcast;
import com.hazelcast.core.HazelcastInstance;

//tag::consumer[]
public class ConsumerMember {

    public static void main( String[] args ) throws Exception {
        HazelcastInstance hz = Hazelcast.newHazelcastInstance();
        IQueue<Integer> queue = hz.getQueue( "queue" ); // <1>
        while ( true ) {
            int item = queue.take(); // <2>
            System.out.println( "Consumed: " + item );
            if ( item == -1 ) {
                queue.put( -1 );
                break;
            }
            Thread.sleep( 5000 ); // <3>
        }
        System.out.println( "Consumer Finished!" );
    }
}
//end::consumer[]
